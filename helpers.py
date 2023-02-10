from sqlalchemy import create_engine
from secret import secret, agentList
import mysql.connector
from mysql.connector import errorcode
import requests
import pandas
import time
import csv
from bs4 import BeautifulSoup as bs
import random
from MySQLdb import _mysql


def getCasePrefix(rangeId):
    rangeToCasePrefixMap = {"A":"EAC","B":"VSC","C":"WAC", "D":"CSC","E":"LIN","F":"NSC","G":"SRC","H":"TSC","I":"MSC","J":"NBC","K":"IOE","L":"YSC"}
    return rangeToCasePrefixMap[rangeId[0:1]]

def getRangeId(case_number):
    RangeIdPrefixByFo = {"EAC":"A", "VSC":"B","WAC":"C", "CSC":"D","LIN":"E","NSC":"F","SRC":"G","TSC":"H","MSC":"I","NBC":"J","IOE":"K","YSC":"L"}
    RangeIdPrefix = RangeIdPrefixByFo.get(case_number[0:3])
    if len(case_number)!=13 or RangeIdPrefix==None:
        return None
    lastFiveDigs=case_number[8:]
    RangeIdSuffix = "0" if int(lastFiveDigs)<49999 else "1"
    return RangeIdPrefix + case_number[3:8] + RangeIdSuffix

def databaseConnect(schema):
    try:
        cnx = mysql.connector.connect(user='root', password=secret,
                                host='127.0.0.1',
                                database=schema)
        return cnx
    except mysql.connector.Error as err:
        print("Something went wrong: {}".format(err))

def databaseClose(cnx):
    cnx.close()

# def dbConnect():
#     try:
#         db=_mysql.connect('immigence.cor389u8xll2.us-east-1.rds.amazonaws.com',"admin", secret,"immigence")
#     except:
#         print("no connection")       


def scrapeSingle(case_number):
    url = "https://egov.uscis.gov/casestatus/mycasestatus.do"
    currAgent = agentList[random.randint(0, 10000)]
    headers = {'user-agent': currAgent}
    data = {"appReceiptNum":case_number, "initCaseSearch":"CHECK+STATUS", "changeLocale":""}
    result = requests.post(url, verify=False, data=data, headers=headers)                                                                                
    soup = bs(result.text, 'html.parser')
    
     #valid cases: resultTitle and resultContent contain case information, and error variable is none
     #invalid cases: error case logs "You have the following errors:"
    resultTitle = soup.h1.string
    resultContent = soup.p.contents[0]
    print("scrapeSingle showing resultTitle for case" + str(case_number))
    
    if soup.h4!=None: 
        if soup.h4.string=="You have the following errors:":
            print("h4 exists and shows You have the following errors")
            return None
    result = dict()
    result['title'] = resultTitle
    result['content'] = resultContent
    return result

    

# def batchScrape(rangeId):
#     K091781

def createRangeQueryableTable(rangeId):
    cnx = databaseConnect("QueryableCases")
    if cnx!=None:
        cursor = cnx.cursor()
        query = ("CREATE TABLE " + rangeId + " LIKE A001450")
        try:
            cursor.execute(query)
        except:
            print("Creating new table failed")


def createRangeLogTable(rangeId):
    cnx = databaseConnect("QueryableCases")
    if cnx!=None:
        cursor = cnx.cursor()
        query = ("CREATE TABLE " + rangeId + " LIKE A001450")
        try:
            cursor.execute(query)
        except:
            print("Creating new table failed")

def populateRangeTable(rangeId):
    cnx=databaseConnect("QueryableCases")
    if cnx!=None:
        case_stub = getCasePrefix(rangeId)+rangeId[1:6]
        cursor = cnx.cursor()

        base=0 if rangeId[6]==0 else 50000
        addOn = 0
        while (addOn<50000):
            
            copy = str(base+addOn)
            i=0
            while i<5-len(str(base+addOn)):
                copy=str(0)+copy
                i+=1
            caseNumber = case_stub + copy
            try:
                query = ("INSERT INTO " +rangeId + " (CaseNumber) values (%s)")
                cursor.execute(query,(caseNumber,))
            except:
                addOn+=1
            addOn+=1
    else:
        print("populating range table failed due to database Connection")
    cnx.commit()
    cursor.close()
    databaseClose(cnx)

def rangeExist(rangeId):
    cnx = databaseConnect("QueryableCases")
    if cnx!=None:
        cursor = cnx.cursor()
        query = ("SHOW TABLES" )
        cursor.execute(query)
        ret = False
        for table in cursor:
            #a table exists, now check that it actually has rows (in case createNewRange stopped midway)
            if table[0] == rangeId:
                ret = True
                # cursorToCountRow = cnx.cursor()
                # query = ("Select count(*) from "+rangeId)
                # cursorToCountRow.execute(query)
                # for count in cursorToCountRow: 
        cursor.close()
        databaseClose(cnx)
        return ret

    # engine = create_engine("immigence.cor389u8xll2.us-east-1.rds.amazonaws.com")

# Most returned case status from USCIS website contains the case type, 
# check if this case type is the same as user-submitted case type. USCIS' type is source of truth
# for some case status on the website, no case type is indicated, in this case keep user-submitted case type
def checkType(petition_type, resultContent):
    case_types = ["I-485", 'I-140', 'I-765', 'I-821', 'I-131', 'I-129', 'I-539', 'I-130', 'I-90', 'N-400']
    first_line = resultContent[0:100]
    # print(first_line)
    true_type = petition_type
    res_has_type = False
    for case_type in case_types:
        if case_type in first_line: 
            res_has_type = True
            if case_type != true_type:
                true_type = case_type
            break
    if petition_type!="N-400" and res_has_type == False and "oath" in first_line:
        true_type = "N-400"
    return true_type

def getStatusCode(resultTitle):
    if "Case Was Received" in resultTitle:
        return 1
    if "Actively Reviewed" in resultTitle:
        return 2
    if "Evidence" in resultTitle:
        if "Sent" in resultTitle:
            return 3
        if "Received" in resultTitle:
            return 4
    if "Interview" in resultTitle:
        if "Case is Ready" in resultTitle:
            return 5
        if "Scheduled" in resultTitle:
            return 6
    if "Denied" in resultTitle:
        return 7
    if "Case Was Updated" in resultTitle:
        return 8
    if "Case Was Approved" in resultTitle:
        return 9
    if "Picked Up" in resultTitle:
        return 10
    if "Delivered" in resultTitle:
        return 11
    if "Certificate Of Naturalization" in resultTitle:
        return 13
    if "New Card" in resultTitle:
        return 15
    return 14
   
    
    

        
    

def getStatusText(status_code):
    status_types = {1:"Case Received & Notice Sent",
                    2:"Case Actively Reviewed", 
                    3:"RFE Requested", 
                    4:"RFE Received",
                    5:"Ready For Interview",
                    6:"Interview Scheduled", 
                    7:"Denied", 
                    8:"Fingerprints were taken",
                    9:"Case Approved", 
                    10:"Card Picked Up",
                    11: "Card Delivered", 
                    12:"Oath Ceremony Notice Mailed",
                    13:"Certificate Of Naturalization Issued",
                    14:"Other",
                    15: "New Card Is Being Produced"
                    }
    return status_types.get(status_code)

def caseInited(cursor, caseNumber):
    query="Select StatusCode from "+getRangeId(caseNumber)+" WHERE CaseNumber = %s"
    cursor.execute(query, (caseNumber,))
    bool =cursor.fetchone()[0] != None
    if bool:
        print("************************************** CASE INITIATED ALREADY")
    #if no result, the caseNumber has not been initialized
    return bool


def caseDeleted(cursor, caseNumber):
    rangeId = getRangeId(caseNumber)
    query="select exists (select * from "+rangeId+" where CaseNumber = %s)"
    cursor.execute(query, (caseNumber,))
    bool = cursor.fetchall()[0][0]==0
    if bool:
         print("************************************** CASE DELETED ALREADY")
    return bool
    