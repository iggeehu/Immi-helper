from constants import CASE_PREFIX, CASE_TYPES
from secret import agentList
from random import randint, sample as sample
import requests
from bs4 import BeautifulSoup as bs
import random
from helpers.checks import rangeLogTableExist, rangeTablePopulated
from helpers.dbConnect import DatabaseConnect, databaseConnect
from helpers.conversions import getCasePrefix, parseUserRequest
import datetime


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
    print("scrapeSingle SCANNING" + str(case_number))
    
    if soup.h4!=None: 
        if soup.h4.string=="You have the following errors:":
            print("h4 exists and shows You have the following errors")
            return None
    result = dict()
    
    result['title'] = resultTitle
    result['content'] = resultContent

    return result


def createRangeQueryableTable(rangeId):
    with DatabaseConnect("QueryableCases") as (cnx,cursor):
        if cnx!=None:
            query = ("CREATE TABLE " + rangeId + " LIKE A001450")
            try:
                cursor.execute(query)
            except:
                print("Creating new table failed")


def createRangeLogTable(rangeId):
    if not rangeLogTableExist(rangeId):
        with DatabaseConnect("RangeLog") as (cnx,cursor):
            tableName = "R"+rangeId
            if cnx!=None:
                query = ("CREATE TABLE " + tableName + " LIKE RA001450")
                try:
                    cursor.execute(query)
                except:
                    print("Creating new table failed")
            else:
                    print("db connection failed")
         




def populateRangeTable(rangeId):
    if not rangeTablePopulated(rangeId):
        with DatabaseConnect("QueryableCases") as (cnx,cursor):
        
            if cnx!=None:
                case_stub = getCasePrefix(rangeId)+rangeId[1:7]
                base=0 if rangeId[7]=="0" else 5000
                addOn = 0
                while (addOn<5000):
                    
                    copy = str(base+addOn)
                    i=0
                    while i<4-len(str(base+addOn)):
                        copy=str(0)+copy
                        i+=1
                    caseNumber = case_stub + copy
                    print(caseNumber)
                    try:
                        query = ("INSERT INTO " +rangeId + " (CaseNumber) values (%s)")
                        cursor.execute(query,(caseNumber,))
                    except:
                        addOn+=1
                    addOn+=1

            else:
                print("populating range table failed due to database Connection")        

    else:
        return

def addToDistributionTable(rangeId):
 
        caseTypes = {"I-140":0,"I-765":0,"I-821":0,"I-131":0,"I-129":0,"I-539":0,
        "I-130":0,"I-90":0,"I-485":0,"N-400":0, "I-751":0, "I-824":0, "Approv":0, 
        "OtherS":0}
        with DatabaseConnect("QueryableCases") as (cnx, cursor):

            for caseType in caseTypes.keys():
                query="Select count(*) from "+rangeId+ " where caseType=%s"
                cursor.execute(query, (caseType,))
                count = cursor.fetchone()[0]
                caseTypes[caseType]=count
            
            caseTypes["Invalid"]=0
            query = "Select count(*) from "+rangeId+ " where caseType is null"
            cursor.execute(query)
            caseTypes["Invalid"]=cursor.fetchone()[0]

            
            with DatabaseConnect("TypeDistribution") as (cnx2, cursor2):
                query2="INSERT IGNORE INTO TypeDistribution (RangeId) values (%s) "
                cursor2.execute(query2,(rangeId,))
                query3 = "UPDATE TypeDistribution set I485=%s, I765=%s, I129=%s, \
                    I130=%s, N400=%s, I539=%s, I131=%s, I821=%s, I140=%s, I90=%s, I751=%s, I824=%s, \
                    InvalidCases=%s, ApprovedAndUnknown=%s, OtherStatusAndUnknown=%s    \
                    Where RangeId = %s"
                cursor2.execute(query3, (caseTypes["I-485"],caseTypes["I-765"],
                caseTypes["I-129"],caseTypes["I-130"],caseTypes["N-400"],
                caseTypes["I-539"],caseTypes["I-131"],caseTypes["I-821"],
                caseTypes["I-140"],caseTypes["I-90"], 
                caseTypes["I-751"], caseTypes["I-824"], caseTypes["Invalid"],
                caseTypes["Approv"], caseTypes["OtherS"], rangeId))

                

def returnAllRanges():
    with DatabaseConnect("TypeDistribution") as (cnx, cursor):
        try:
            query= "SELECT * FROM TypeDistribution"
            cursor.execute(query)
            listTups=cursor.fetchall()
            list = []
            for tup in listTups:
                list.append(tup[0])
            return list
        except:
            raise ConnectionError("DB connection failed")

#return dict {"EAC":[(case, casetype), (case, casetype)]}        
def getTodayApprovedCases():
    todayApprovedDict = {}
    for prefix in CASE_PREFIX:
        todayApprovedDict[prefix]={}
        for casetype in CASE_TYPES:
            todayApprovedDict[prefix][casetype]=[]
    with DatabaseConnect("ApprovedCasesToday") as (cnx, cursor):
        try:
            query="SELECT caseNumber, caseType FROM ApprovedCasesToday where ApprovalTime>now()-interval 24 hour"
            cursor.execute(query)
            listTups=cursor.fetchall()
            print(todayApprovedDict)
            for tup in listTups:
                if tup[1]=="" or tup[1]==None:
                    continue
                prefix = tup[0][0:3]
                casetype = tup[1]
                todayApprovedDict[prefix][casetype].append(tup[0])
            
            return todayApprovedDict
        except:
            raise("Failure reaching the database")

def addToApproved(caseNumber, caseType):
    print("!!!!!!!!!!!NEW APPROVED CASE "+ caseNumber + "WOOHOO!!!!!!!!!!!!!!!!!!!!!!!!")
    dt_string=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with DatabaseConnect("ApprovedCasesToday") as (cnx2approved, cursor2approved):
        try:
            print("DatabaseConnect called " + caseNumber + caseType + dt_string)
            addQuery = "INSERT INTO ApprovedCasesToday (CaseNumber, CaseType, ApprovalTime) values (%s, %s, %s)"
            cursor2approved.execute(addQuery, (caseNumber, caseType,  dt_string))
        except:
            print("something went wrong when adding case to approved database")
