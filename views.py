from concurrent.futures.thread import _worker
from flask import Blueprint, render_template, request, redirect, url_for
from bs4 import BeautifulSoup as bs
from h11 import Data
from Visualizations.perCaseType.statusLineGraph import outputStatusPerTypeDictAndGraph

from helpers.getCases import getAllRanges, getStatusDataPerTypeDict, getScannerPercentage
from helpers.dbOperations import getTodayApprovedCases, scrapeSingle, createRangeLogTable, addToDistributionTable, createRangeQueryableTable, returnAllRanges
from helpers.conversions import getRangeId, getStatusCode, getRangeText, scrapeAll, parseUserRequest
from helpers.checks import checkType, rangeExist
from helpers.dbConnect import DatabaseConnect
from Visualizations.caseTypePie import outputPlot
from workers import batchScrape, checkAndFillRange
from rq import Queue, Retry
from redis import Redis
from constants import CASE_TYPES
from bokeh.embed import components
from datetime import date, datetime
import os
import json
from customWorker import conn

# conn = Redis()


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

@views.route("/displayRanges")
def displayRanges():
  
    #if deployed
    #webCache = Redis.from_url(redis_url)
    redisResult = conn.get("rangeToTextPercentageDict")
    if redisResult:
        rangeToTextPercentageDict = json.loads(redisResult)
    else:
        rangeList = getAllRanges()
        rangeToTextPercentageDict = {}
        for range in rangeList:
            rangeToTextPercentageDict[range]=(getRangeText(range), getScannerPercentage(range))
        conn.set("rangeToTextPercentageDict", json.dumps(rangeToTextPercentageDict), ex=300)
    nowTime=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template("range.html", rangeToTextPercentageDict=rangeToTextPercentageDict, nowTime = nowTime)

@views.route('/handle_data', methods=['POST'])
def handle_data():

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
            query="Select count(*) from UserInfo where CaseNumber=%s"
            cursor.execute(query, (case_number,))
            tup = cursor.fetchone()
            if tup[0]==0:
                query="INSERT INTO UserInfo (CaseNumber, CaseSubType, State, HomeCountry, PetitionDate, StatusCode) values(%s, %s, %s, %s, %s, %s)"
                cursor.execute(query,(case_number, petition_type, form["state"], form["home_country"], form["petition_date"], status_code))
    
    rangeId=getRangeId(case_number)
    if not rangeExist(rangeId):
        userPromptedWorkerQueue = Queue('default', connection=conn)

        createRangeJob = userPromptedWorkerQueue.enqueue('helpers.dbOperations.createRangeQueryableTable', rangeId)
        populateRangeJob=userPromptedWorkerQueue.enqueue('helpers.dbOperations.populateRangeTable', rangeId, retry=Retry(max=10, interval=10), 
        depends_on=createRangeJob, job_timeout='24h')
        initScrapeJob = userPromptedWorkerQueue.enqueue('workers.batchScrape', rangeId, retry=Retry(max=10, interval=10), depends_on=populateRangeJob)
        addToDistributionTableJob=userPromptedWorkerQueue.enqueue('helpers.dbOperations.addToDistributionTable', rangeId, retry=Retry(max=10, interval=10), depends_on=initScrapeJob)
        createRangeLogTableJob=userPromptedWorkerQueue.enqueue('helpers.dbOperations.createRangeLogTable', rangeId, retry=Retry(max=10, interval=10), depends_on=initScrapeJob)
        return render_template("checkBacklater.html")
    else:
        # populateRangeJob=init.enqueue('helpers.dbOperations.populateRangeTable', rangeId, retry=Retry(max=10, interval=10),job_timeout='24h')
        # dailyScrapeJob = init.enqueue('workers.batchScrape', rangeId, retry=Retry(max=10, interval=10),job_timeout='24h', depends_on= populateRangeJob)
        # createRangeLogTableJob = init.enqueue('helpers.dbOperations.createRangeLogTable', rangeId, retry=Retry(max=10, interval=10), depends_on=dailyScrapeJob)
        # checkAndFillRangeLogJob = init.enqueue('workers.checkAndFillRange', rangeId, retry=Retry(max=10, interval=10), depends_on=createRangeLogTableJob)
        # addToDistributionTable(rangeId)
        return redirect(url_for('views.caseData', rangeId = rangeId))

@views.route("/invalid")
def invalid():
    return render_template("invalid.html")
    
@views.route('/caseData/<rangeId>', methods=['GET'])
def caseData(rangeId):
    script = conn.get("script").decode('ASCII') if conn.get("script")!=None else None
    divDist = conn.get("divDist").decode('ASCII') if conn.get("divDist")!=None else None
    divTable = conn.get("divTable").decode('ASCII') if conn.get("divDist")!=None else None
    dataByTypeDict = json.loads(conn.get("dataByTypeDict")) if conn.get("dataByTypeDict")!=None else None
    statusGraphDict=json.loads(conn.get("statusGraphDict")) if conn.get("statusGraphDict")!=None else None
    if script == None or divDist == None or divTable ==None or dataByTypeDict ==None or statusGraphDict ==None:
        distGraph, dataTable = outputPlot(rangeId)
        statusGraphDict=outputStatusPerTypeDictAndGraph(rangeId)
    #{'I-485':[date, 135, 543, 654,....], 'I-765':[date, 453, 21, 54, ...]}
   
    #{'I-485': , 'I-765': 834, ...}
        dataByTypeDict = getStatusDataPerTypeDict(rangeId)
        if statusGraphDict==None:
            return render_template("checkBacklater.html")
        else:
            script, divTups = components((distGraph, dataTable, *statusGraphDict.values()))
            divDist = divTups[0]
            print(divDist)
            divTable = divTups[1]
            caseTypeDivs = divTups[2:]
            DivDicts = {}
            i=0
            for key in statusGraphDict.keys():
                statusGraphDict[key]=caseTypeDivs[i]
                i+=1
        conn.set("script", script, ex=300)
        conn.set("divDist", divDist, ex=300)
        conn.set("divTable", divTable, ex=300)
        conn.set("dataByTypeDict", json.dumps(dataByTypeDict), ex=300)
        conn.set("statusGraphDict", json.dumps(statusGraphDict), ex=300)
        
    
    return render_template("caseData.html", rangeText=getRangeText(rangeId), 
    script = script, divDist = divDist, divTable = divTable, dataByTypeDict=dataByTypeDict, statusGraphDict=statusGraphDict)
     

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
def populateRangeLog():
    rangesList = returnAllRanges()
    for range in rangesList:
        
        init = Queue('default', connection=conn)
        createRangeLogTable(range)
        checkAndFillRange(range)
        # createRangeLogTableJob = init.enqueue('helpers.dbOperations.createRangeLogTable', range, retry=Retry(max=10, interval=10))
        # checkAndFillRangeLogJob = init.enqueue('workers.checkAndFillRange', range, retry=Retry(max=10, interval=10), depends_on=createRangeLogTableJob)
    return render_template("checkBacklater.html")
 
