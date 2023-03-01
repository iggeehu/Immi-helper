from concurrent.futures.thread import _worker
from flask import Blueprint, render_template, request, redirect, url_for
from bs4 import BeautifulSoup as bs
from h11 import Data
from Visualizations.perCaseType.statusLineGraph import outputStatusLineGraph

from helpers.getCases import getAllRanges
from helpers.dbOperations import getTodayApprovedCases, scrapeSingle, createRangeLogTable, addToDistributionTable, createRangeQueryableTable, returnAllRanges
from helpers.conversions import getRangeId, getStatusCode, getRangeText, scrapeAll, parseUserRequest
from helpers.checks import checkType, rangeExist
from helpers.dbConnect import DatabaseConnect
from Visualizations.caseTypePie import outputPlot
from workers import batchScrape
from rq import Queue, Retry
from redis import Redis
from constants import CASE_TYPES
from bokeh.embed import components
from datetime import date, datetime
from customWorker import conn

# from Visualizations.caseTypePie import script, div




views = Blueprint(__name__, "views")

@views.route("/")
def home():

    todayApprovedDict=getTodayApprovedCases()
    todayString = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template("home.html", todayApprovedDict=todayApprovedDict, caseTypes = CASE_TYPES, today=todayString)

@views.route("/about")
def about():
    return render_template("about.html")

@views.route("/contact")
def contact():
    return render_template("contact.html")

@views.route("/invalid")
def invalid():
    return render_template("invalid.html")

@views.route("/displayRanges")
def displayRanges():
    rangeList = getAllRanges()
    rangeToText = {}
    for range in rangeList:
        rangeToText[getRangeText(range)]=range
    return render_template("range.html", rangeToText=rangeToText)

@views.route('/handle_data', methods=['POST'])
def handle_data():
    # conn = Redis()
    init = Queue('default', connection=conn)

    form=parseUserRequest(request)
    if form["case_number"]=="" or form["petition_date"]=="" or form["petition_type"]=="" or form["home_country"]=="" or form["state"]=="":
        return redirect(request.referrer)

    case_number = form["case_number"]

    result = scrapeSingle(case_number)
    if result==None:
        return render_template("invalid.html")

    petition_type=checkType(form["petition_type"], result['content'])
  
    #store inquirer's information
    if petition_type!="Other":
        status_code=getStatusCode(result['title']) 
        with DatabaseConnect("UserInfo") as (cnx, cursor):
            query="INSERT INTO Users (CaseNumber, CaseType, State, HomeCountry, PetitionDate, StatusCode) values(%s, %s, %s, %s, %s, %s)"
            cursor.execute(query,(case_number, petition_type, form["state"], form["home_country"], form["petition_date"], status_code))
    #

    #ifRangeExists, retrieve data from DB
        #put data into visualization API
            #save charts and render on the front end
    rangeId=getRangeId(case_number)
    if not rangeExist(rangeId):
        print("range Does Not Exist")
        createRangeJob = init.enqueue('helpers.dbOperations.createRangeQueryableTable', rangeId)
        populateRangeJob=init.enqueue('helpers.dbOperations.populateRangeTable', rangeId, retry=Retry(max=10, interval=10), 
        depends_on=createRangeJob, job_timeout='24h')
        initScrapeJob = init.enqueue('workers.batchScrape', rangeId, retry=Retry(max=10, interval=10), depends_on=populateRangeJob)
        addToDistributionTableJob=init.enqueue('helpers.dbOperations.addToDistributionTable', rangeId, retry=Retry(max=10, interval=10), depends_on=initScrapeJob)
        createRangeLogTableJob=init.enqueue('helpers.dbOperations.createRangeLogTable', rangeId, retry=Retry(max=10, interval=10), depends_on=initScrapeJob)
        return render_template("checkBacklater.html")
    else:
        populateRangeJob=init.enqueue('helpers.dbOperations.populateRangeTable', rangeId, retry=Retry(max=10, interval=10),job_timeout='24h')
        dailyScrapeJob = init.enqueue('workers.batchScrape', rangeId, retry=Retry(max=10, interval=10),job_timeout='24h', depends_on= populateRangeJob)
        createRangeLogTableJob = init.enqueue('helpers.dbOperations.createRangeLogTable', rangeId, retry=Retry(max=10, interval=10), depends_on=dailyScrapeJob)
        checkAndFillRangeLogJob = init.enqueue('workers.checkAndFillRange', rangeId, retry=Retry(max=10, interval=10), depends_on=createRangeLogTableJob)
        addToDistributionTable(rangeId)
        return redirect(url_for('views.caseData', rangeId = rangeId))

@views.route('/caseData/<rangeId>', methods=['GET'])
def caseData(rangeId):
    distGraph, dataTable = outputPlot(rangeId)
    statusGraphDict = outputStatusLineGraph(rangeId)
    if statusGraphDict==None:
        return render_template("checkBacklater.html")
    else:
        script, divTups = components((distGraph, dataTable, *statusGraphDict.values()))
        divDist = divTups[0]
        divTable = divTups[1]
        caseTypeDivs = divTups[2:]
        DivDicts = {}
        i=0
        for key in statusGraphDict.keys():
            statusGraphDict[key]=caseTypeDivs[i]
            i+=1
        return render_template("caseData.html", rangeText=getRangeText(rangeId), 
        script = script, divDist = divDist, divTable = divTable, statusGraphDict=statusGraphDict)
     

@views.route('/scrapeAll', methods=['GET'])  
def scrapeAdmin():
    rangesList = returnAllRanges()
    for range in rangesList:
        init = Queue('default', connection=conn)
        dailyScrapeJob = init.enqueue('workers.batchScrape', range, retry=Retry(max=10, interval=10),job_timeout='24h')
        createRangeLogTableJob = init.enqueue('helpers.dbOperations.createRangeLogTable', range, retry=Retry(max=10, interval=10), depends_on=dailyScrapeJob)
        checkAndFillRangeLogJob = init.enqueue('workers.checkAndFillRange', range, retry=Retry(max=10, interval=10), depends_on=createRangeLogTableJob)
    return render_template("checkBacklater.html")
 

     
@views.route('/createRangeAll', methods=['GET'])  
def scrapeAdmin():
    rangesList = returnAllRanges()
    for range in rangesList:
        init = Queue('default', connection=conn)
        createRangeLogTableJob = init.enqueue('helpers.dbOperations.createRangeLogTable', range, retry=Retry(max=10, interval=10))
        checkAndFillRangeLogJob = init.enqueue('workers.checkAndFillRange', range, retry=Retry(max=10, interval=10), depends_on=createRangeLogTableJob)
    return render_template("checkBacklater.html")
 
