from distutils.log import error
from xmlrpc.client import DateTime
from helpers import scrapeSingle, databaseConnect, databaseClose, getCasePrefix, checkType, getStatusCode,caseInited, ScrapeEligibles
import numpy
from random import randint as rand, sample as sample
from time import sleep
import datetime
from constants import SAMPLE_SIZE

#goal: delete invalid cases from the table that stores the range's queryable cases, populate initial status code
def initBatchScrape(rangeId):
    # print("rangeId from init:" + rangeId)
    
    cnx=databaseConnect("QueryableCases")
    numOfTries=0
    if cnx!=None:
        cursor = cnx.cursor()
        case_stub = getCasePrefix(rangeId)+rangeId[1:6]
        pool = range(50000, 99999) if rangeId[6]=='1' else range(0, 49999)
        
        randomizedPool = sample(pool, 49999)
        
        for number in randomizedPool:
            numOfTries+=1
            if numOfTries%100==0:
                sleep(15)
            
            caseNumber = case_stub + str(number)
            if not caseInited(cursor, caseNumber):
                try:
                    caseResult = scrapeSingle(caseNumber)
                    if caseResult!=None:
                        title=caseResult['title']
                        content=caseResult['content']
                        caseType = checkType("", content)
                        statusCode = getStatusCode(title)
                        now = datetime.datetime.now()
                        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
                        query ="UPDATE " +rangeId+ " SET caseType = %s, statusCode = %s, lastFetched = %s WHERE CaseNumber = %s"
                        cursor.execute(query, (caseType, statusCode, dt_string, caseNumber))
                except:
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!EXCEPTIONNN")
                    print(numOfTries)
                    sleep(30)
                    initBatchScrape(rangeId)
            else:
                print("Nothing to scrape")
            # sleep(rand(1, 2))
            cnx.commit()
        cursor.close()
        
    else:
        print('initial Batch scan failed due to database connection issues')
    databaseClose(cnx)
       
def dailyScrape(rangeId):    
    ScrapeEligibles(rangeId, ("StatusCode", [2,4,6,8]))
    # ReadToRangeLog(rangeId)

def weeklyScrape(rangeId):
    ScrapeEligibles(rangeId, ())
    # ReadToRangeLog(rangeId)

def ScrapeEmpties(rangeId):
    ScrapeEligibles(rangeId, ("statusCode", [None]))