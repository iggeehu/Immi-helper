from distutils.log import error
from xmlrpc.client import DateTime
from helpers import scrapeSingle, databaseConnect, databaseClose, scrapeComplete, getCasePrefix, checkType, getStatusCode,caseInited, ScrapeEligibles, updatedToday
import numpy
from random import randint as rand, sample as sample
from time import sleep
import datetime
from constants import SAMPLE_SIZE

#goal: delete invalid cases from the table that stores the range's queryable cases, populate initial status code
def weeklyScrape(rangeId):
    # print("rangeId from init:" + rangeId)

    cnx=databaseConnect("QueryableCases")
    numOfTries=0
    if cnx!=None:
        cursor = cnx.cursor()
        if(scrapeComplete(cursor, rangeId)):
            return
        case_stub = getCasePrefix(rangeId)+rangeId[1:6]
        pool = range(50000, 99999) if rangeId[6]=='1' else range(0, 49999)
        
        randomizedPool = sample(pool, 49999)
        
        for number in randomizedPool:
            numOfTries+=1
            if numOfTries%100==0:
                sleep(15)
            
            caseNumber = case_stub + str(number)
            if not caseInited(cursor, caseNumber) and not updatedToday(cursor, caseNumber):
                try:
                    caseResult = scrapeSingle(caseNumber)
                    now = datetime.datetime.now()
                    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
                    if caseResult!=None:
                        title=caseResult['title']
                        content=caseResult['content']
                        caseType = checkType("", content)
                        statusCode = getStatusCode(title)
                        query ="UPDATE " +rangeId+ " SET caseType = %s, statusCode = %s, lastFetched = %s WHERE CaseNumber = %s"
                        cursor.execute(query, (caseType, statusCode, dt_string, caseNumber))
                    else:
                        query ="UPDATE " +rangeId+ " SET lastFetched = %s WHERE CaseNumber = %s"
                        cursor.execute(query, (dt_string, caseNumber))

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


def ScrapeEmpties(rangeId):
    ScrapeEligibles(rangeId, ("statusCode", [None]))