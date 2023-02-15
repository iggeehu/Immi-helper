from flask import Blueprint, render_template, request, redirect, url_for
from bs4 import BeautifulSoup as bs

from helpers.dbOperations import scrapeSingle, createRangeLogTable, addToDistributionTable
from helpers.conversions import getRangeId, getStatusCode
from helpers.checks import checkType, rangeExist
from helpers.dbConnect import databaseClose, databaseConnect

from workers import weeklyScrape
from rq import Queue, Retry
from redis import Redis
# from Visualizations.caseTypePie import script, div




views = Blueprint(__name__, "views")

@views.route("/")
def home():
    return render_template("home.html")

@views.route("/invalid")
def invalid():
    return render_template("invalid.html")

@views.route('/handle_data', methods=['POST'])
def handle_data():
    redis_conn = Redis()
    init = Queue('high', connection=redis_conn)

    case_number = request.form['case_number']
    petition_date = request.form['petition_date']
    petition_type = request.form['petition_type']
    home_country = request.form['country']
    state = request.form['state']
    if case_number=="" or petition_date=="" or petition_type=="" or home_country=="" or state=="":
        return redirect(request.referrer)

    result = scrapeSingle(case_number)
    petition_type=checkType(petition_type, result['content'])
    rangeId=getRangeId(case_number)
    result = scrapeSingle(case_number)
   
   
       
    #user typed in invalid case
    if result==None:
        return render_template("invalid.html")

    #store inquirer's information
    if petition_type!="Other":
       
        status_code=getStatusCode(result['title']) 
        cnx=databaseConnect("UserInfo")
        cursor=cnx.cursor()
        query="INSERT INTO Users (CaseNumber, CaseType, State, HomeCountry, PetitionDate, StatusCode) values(%s, %s, %s, %s, %s, %s)"
        cursor.execute(query,(case_number, petition_type, state, home_country, petition_date, status_code))

        cursor.close()
        cnx.commit()
        databaseClose(cnx)

    #ifRangeExists, retrieve data from DB
        #put data into visualization API
            #save charts and render on the front end

    if not rangeExist(rangeId):
        print("range Does Not Exist")

        createRangeJob = init.enqueue('helpers.dbOperations.createRangeQueryableTable', rangeId)
        populateRangeJob=init.enqueue('helpers.dbOperations.populateRangeTable', rangeId, retry=Retry(max=10, interval=10), 
        depends_on=createRangeJob, job_timeout='24h')
        initScrapeJob = init.enqueue('workers.weeklyScrape', rangeId, retry=Retry(max=10, interval=10), depends_on=populateRangeJob)
        addToDistributionTableJob=init.enqueue('helpers.dbOperations.addToDistributionTable', rangeId, retry=Retry(max=10, interval=10), depends_on=initScrapeJob)
        createRangeLogTableJob=init.enqueue('helpers.dbOperations.createRangeLogTable', rangeId, retry=Retry(max=10, interval=10), depends_on=initScrapeJob)
        return render_template("checkBacklater.html")
    else:
        dailyScrapeJob = init.enqueue('workers.dailyScrape', rangeId, retry=Retry(max=10, interval=10),job_timeout='24h')
        createRangeLogTableJob = init.enqueue('helpers.dbOperations.createRangeLogTable', rangeId, retry=Retry(max=10, interval=10))
        checkAndFillRangeLogJob = init.enqueue('workers.checkAndFillRange', rangeId, retry=Retry(max=10, interval=10), depends_on=createRangeLogTableJob)
        addToDistributionTable(rangeId)
        return redirect(url_for('views.caseData', rangeId=rangeId))

@views.route('/caseData/<rangeId>', methods=['GET'])
def caseData(rangeId):
    return render_template("caseData.html")

    
   
    
    # outputRaw = pullFromDb(rangeId)
    # outputCharts = visualizationApi(outputRaw)
   


    return render_template("home.html")

