from distutils.log import error
from xmlrpc.client import DateTime
from helpers.dbConnect import DatabaseConnect

from helpers.dbOperations import databaseConnect, scrapeSingle, createRangeLogTable
from helpers.getCases import casesNotUpdatedToday, NearApprovalAndFreshOrUnscanned, casesNeverScanned
from helpers.conversions import getStatusCode
from helpers.checks import checkType, isLogUpdatedToday, rangeLogTableExist


import numpy
from random import randint as rand, sample as sample
from time import sleep
import datetime
from constants import SAMPLE_SIZE


#goal: delete invalid cases from the table that stores the range's queryable cases, populate initial status code
def batchScrape(rangeId, frequency:str = "daily"):
    # print("rangeId from init:" + rangeId)
    with DatabaseConnect("QueryableCases") as cnx:
        if cnx!=None:
            cursor = cnx.cursor()
            if frequency == "daily":
                list= NearApprovalAndFreshOrUnscanned(cursor, rangeId)
            else:
                list = casesNotUpdatedToday(cursor, rangeId)
            
            while len(list) !=0:
                print(len(list))
                caseNumber = list.pop()
                # try:
                caseResult = scrapeSingle(caseNumber)
                now = datetime.datetime.now()
                dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
                #not an invalid case
                if caseResult!=None:
                    #get scrape result
                    newTitle=caseResult['title']
                    newContent=caseResult['content']
                    newStatusCode = getStatusCode(newTitle)
                    newCaseType = checkType("", newContent)
                
                    #if new statusCode is approved and no type scraped, set "ApprovedUnknown" etc
                    if newStatusCode in [9, 10, 11, 15] and newCaseType == "":
                        newCaseType = "ApprovedUnknown"
                    if newStatusCode in [14] and newCaseType=="":
                        newCaseType = "OtherStatusUnknown"

                    #before updating, get the case's current status and caseType
                    dbQuery = "select caseType, statusCode from "+rangeId+" where caseNumber = %s"
                    cursor.execute(dbQuery, (caseNumber,))
                    dbTup = cursor.fetchone()

                    
                    if dbTup!=None and dbTup[0]!=None:
                        currType = dbTup[0]
                        currStatusCode = dbTup[1]
                        if currStatusCode not in [9, 10, 11, 15] and currStatusCode != None and newStatusCode in [9, 10, 11, 15]:
                            # add to "approvedtoday database"
                            print("!!!!!!!!!!!NEW APPROVED CASE "+ caseNumber + "WOOHOO!!!!!!!!!!!!!!!!!!!!!!!!")
                            with DatabaseConnect("ApprovedCasesToday") as cnx2approved:
                                cursor2approved = cnx2approved.cursor()
                                addQuery = "INSERT INTO ApprovedCasesToday (CaseNumber, CaseType, ApprovalTime) values (%s, %s, %s)"
                                cursor2approved.execute(addQuery, (caseNumber, currType,  dt_string))
                                cnx2approved.commit()
                                cursor2approved.close()
                                newCaseType = currType

            
                    query ="UPDATE " +rangeId+ " SET statusCode = %s, lastFetched = %s, caseType = %s WHERE CaseNumber = %s"
                    cursor.execute(query, (newStatusCode, dt_string, newCaseType, caseNumber))

                    
                #an invalid case, only update lastFetched
                else:
                    query ="UPDATE " +rangeId+ " SET caseType = 'invalid', lastFetched = %s WHERE CaseNumber = %s"
                    cursor.execute(query, (dt_string, caseNumber))

                # except:
                #     print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!EXCEPTIONNN")
                #     sleep(10)
                #     batchScrape(rangeId)
                
                    # sleep(rand(1, 2))
                cnx.commit()
            cursor.close()
            
        else:
            print('initial Batch scan failed due to database connection issues')
            batchScrape(rangeId)

       

    

def checkAndFillRange(rangeId):
    if not rangeLogTableExist(rangeId):
        createRangeLogTable(rangeId)
    with DatabaseConnect("RangeLog") as cnx:
        tableName = "R"+rangeId
        cursor = cnx.cursor()
        now = datetime.datetime.now()
    
        caseTypes = {"I-140":0,"I-765":0,"I-821":0,"I-131":0,"I-129":0,"I-539":0,"I-130":0,"I-90":0,"I-485":0,"N-400":0,"I-751":0, "I-824":0, "Approv":0, "OtherS":0}

        for caseType in caseTypes.keys():
            with DatabaseConnect("QueryableCases") as cnx2:
                cursor2=cnx2.cursor()    
                query="Select StatusCode from "+rangeId+" where CaseType=%s"
                cursor2.execute(query, (caseType,))
                
                statusCodesTups = cursor2.fetchall()
                cursor2.close()

            statusCodesDict ={"Received":0, "ActiveReview":0, "RFEreq":0, 
            "RFErec":0, "IntReady":0, "IntSched":0, "Denied":0, 
            "Approved":0, "Other":0}
            for tup in statusCodesTups:
                if tup[0]==1:
                    statusCodesDict["Received"]+=1
                if tup[0]==2:
                    statusCodesDict["ActiveReview"]+=1
                if tup[0]==3:
                    statusCodesDict["RFEreq"]+=1
                if tup[0]==4:
                    statusCodesDict["RFErec"]+=1
                if tup[0]==5:
                    statusCodesDict["IntReady"]+=1
                if tup[0]==6:
                    statusCodesDict["IntSched"]+=1
                if tup[0]==7:
                    statusCodesDict["Denied"]+=1
                if tup[0]==9 or  tup[0]==10 or tup[0]==11 or tup[0]==12 or tup[0]==13 or tup[0]==15:
                    statusCodesDict["Approved"]+=1
                if tup[0]==14:
                    statusCodesDict["Other"]+=1
                

            # initial insert unless today's already filled
            insertQueryWhenNoDuplicate= "\
                INSERT INTO "+tableName+" (CollectionDate, CaseType, Received,  \
                ActiveReview, RFEreq, RFErec, IntReady, IntSched, Denied, Approved, Other)   \
                select %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s \
                where NOT EXISTS(select * from " +tableName+" where CollectionDate=%s and CaseType=%s)"
                
            cursor.execute(insertQueryWhenNoDuplicate, (now.strftime("%Y-%m-%d"), caseType,
            statusCodesDict["Received"],statusCodesDict["ActiveReview"], 
            statusCodesDict["RFEreq"],statusCodesDict["RFErec"],
            statusCodesDict["IntReady"], statusCodesDict["IntSched"],
            statusCodesDict["Denied"], statusCodesDict["Approved"], statusCodesDict["Other"],
            now.strftime("%Y-%m-%d"), caseType))

            #if filled, update
            insertQueryWhenDuplicate ="UPDATE "+tableName+" set Received=%s,  \
                ActiveReview=%s, RFEreq=%s, RFErec=%s, IntReady=%s, IntSched=%s, \
                Denied=%s, Approved=%s, Other=%s   \
                where CollectionDate=%s and CaseType=%s"
            

            cursor.execute(insertQueryWhenDuplicate, (  
            statusCodesDict["Received"],statusCodesDict["ActiveReview"],  
            statusCodesDict["RFEreq"],statusCodesDict["RFErec"], 
            statusCodesDict["IntReady"], statusCodesDict["IntSched"], 
            statusCodesDict["Denied"], statusCodesDict["Approved"], statusCodesDict["Other"], 
            now.strftime("%Y-%m-%d"), caseType))

            cnx.commit()
        cursor.close()
        






