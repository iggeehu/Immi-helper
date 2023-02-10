from distutils.log import error
from xmlrpc.client import DateTime
from helpers import scrapeSingle, databaseConnect, databaseClose, getCasePrefix, checkType, getStatusCode, caseDeleted, caseInited
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
            if not caseDeleted(cursor, caseNumber) and not caseInited(cursor, caseNumber):
                
                caseResult = scrapeSingle(caseNumber)
                if caseResult!=None:
                    title=caseResult['title']
                    content=caseResult['content']
                    caseType = checkType("", content)
                    statusCode = getStatusCode(title)
                    now = datetime.datetime.now()
                    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
                    # print(statusCode)
                    try:
                        query ="UPDATE " +rangeId+ " SET caseType = %s, statusCode = %s, lastFetched = %s WHERE CaseNumber = %s"
                        cursor.execute(query, (caseType, statusCode, dt_string, caseNumber))
                       
                    except:
                        print(numOfTries)
                        sleep(30) #alternatively rotate IP, how to do?
                    
                else:
                    query = "DELETE FROM " + rangeId + " WHERE CaseNumber = %s"
                    cursor.execute(query, (caseNumber,))
                
            # sleep(rand(1, 2))
            cnx.commit()
        cursor.close()
        
    else:
        print('initial Batch scan failed due to database connection issues')
    databaseClose(cnx)
       

