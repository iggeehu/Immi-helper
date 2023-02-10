from flask import Blueprint, render_template, request, redirect, url_for
from bs4 import BeautifulSoup as bs

from helpers import getRangeId, checkType, rangeExist, scrapeSingle, createRangeQueryableTable, getCasePrefix, populateRangeTable
from workers import initBatchScrape

views = Blueprint(__name__, "views")

@views.route("/")
def home():
    return render_template("home.html")

@views.route("/invalid")
def invalid():
    return render_template("invalid.html")

@views.route('/handle_data', methods=['POST'])
def handle_data():
    case_number = request.form['case_number']
    petition_date = request.form['petition_date']
    petition_type = request.form['petition_type']

    result = scrapeSingle(case_number)
    #user typed in invalid case
    if result==None:
        return render_template("invalid.html")
 
    petition_type=checkType(petition_type, result['content'])
    rangeId=getRangeId(case_number)
   
    #ifRangeExists, retrieve data from DB
        #put data into visualization API
            #save charts and render on the front end
  
    if not rangeExist(rangeId):
        print("range Does Not Exist")
        createRangeQueryableTable(rangeId)
        populateRangeTable(rangeId)
   
    initBatchScrape(rangeId)
    # outputRaw = pullFromDb(rangeId)
    # outputCharts = visualizationApi(outputRaw)
   


    return render_template("home.html")

