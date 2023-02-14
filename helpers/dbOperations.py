from secret import agentList
from random import randint, sample as sample
import requests
from bs4 import BeautifulSoup as bs
import random
from helpers.checks import rangeLogTableExist, rangeTablePopulated
from helpers.dbConnect import databaseConnect, databaseClose

from helpers.conversions import getCasePrefix





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
    cnx = databaseConnect("QueryableCases")
    if cnx!=None:
        cursor = cnx.cursor()

        query = ("CREATE TABLE " + rangeId + " LIKE A001450")
        try:
            cursor.execute(query)
        except:
            print("Creating new table failed")


def createRangeLogTable(rangeId):
    if rangeLogTableExist(rangeId):
        cnx = databaseConnect("RangeLog")
        tableName = "R"+rangeId
        if cnx!=None:
            cursor = cnx.cursor()
            query = ("CREATE TABLE " + tableName + " LIKE RA001450")
            try:
                cursor.execute(query)
            except:
                print("Creating new table failed")



def populateRangeTable(rangeId):
    if not rangeTablePopulated(rangeId):
        cnx=databaseConnect("QueryableCases")
        if cnx!=None:
            case_stub = getCasePrefix(rangeId)+rangeId[1:7]
            cursor = cnx.cursor()

            base=0 if rangeId[7]==0 else 5000
            addOn = 0
            while (addOn<5000):
                
                copy = str(base+addOn)
                i=0
                while i<4-len(str(base+addOn)):
                    copy=str(0)+copy
                    i+=1
                caseNumber = case_stub + copy
                try:
                    query = ("INSERT INTO " +rangeId + " (CaseNumber) values (%s)")
                    cursor.execute(query,(caseNumber,))
                except:
                    addOn+=1
                addOn+=1
                cnx.commit()
        else:
            print("populating range table failed due to database Connection")
        
        cursor.close()
        databaseClose(cnx)
    else:
        return








    
            
