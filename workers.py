from distutils.log import error
from xmlrpc.client import DateTime

from helpers.dbOperations import databaseConnect, databaseClose, scrapeSingle, createRangeLogTable
from helpers.getCases import casesNotUpdatedToday, OneStepBeforeApprovalAndFresh, casesNeverScanned
from helpers.conversions import getStatusCode
from helpers.checks import checkType, isLogUpdatedToday, rangeLogTableExist


import numpy
from random import randint as rand, sample as sample
from time import sleep
import datetime
from constants import SAMPLE_SIZE


#goal: delete invalid cases from the table that stores the range's queryable cases, populate initial status code
def weeklyScrape(rangeId):
    # print("rangeId from init:" + rangeId)
    cnx=databaseConnect("QueryableCases")
    if cnx!=None:
        cursor = cnx.cursor()
        #as long as there are cases that are not updated today
        #if weeklyscrape is run for the first time, use casesNeverScanned, if for weekly jobs, use casesNotUpdatedToday
        list=casesNotUpdatedToday(cursor, rangeId)
        print(list)
        while len(list) !=0:
            print(len(list))
            caseNumber = list.pop()
            
            try:
                caseResult = scrapeSingle(caseNumber)
                now = datetime.datetime.now()
                dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
                #not an invalid case
                if caseResult!=None:
                    title=caseResult['title']
                    content=caseResult['content']
                    caseType = checkType("", content)
                    statusCode = getStatusCode(title)
                    if statusCode in [9, 10, 11, 15] and caseType == "":
                        caseType = "ApprovedUnknown"
                    if statusCode in [14] and caseType=="":
                        caseType = "OtherStatusUnknown"
                    query ="UPDATE " +rangeId+ " SET caseType = %s, statusCode = %s, lastFetched = %s WHERE CaseNumber = %s"
                    cursor.execute(query, (caseType, statusCode, dt_string, caseNumber))
                #an invalid case, only update lastFetched
                else:
                    query ="UPDATE " +rangeId+ " SET lastFetched = %s WHERE CaseNumber = %s"
                    cursor.execute(query, (dt_string, caseNumber))

            except:
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!EXCEPTIONNN")
                sleep(10)
                weeklyScrape(rangeId)
            
                # sleep(rand(1, 2))
            cnx.commit()
        cursor.close()
        
    else:
        print('initial Batch scan failed due to database connection issues')
        weeklyScrape(rangeId)
    databaseClose(cnx)
       
def dailyScrape(rangeId):    
    cnx=databaseConnect("QueryableCases")
    numOfTries=0
    if cnx!=None:
        cursor = cnx.cursor()
        list = OneStepBeforeApprovalAndFresh(cursor,rangeId)
        while len(list)!=0:
            print(len(list))
            caseNumber = list.pop()
            try:
                        caseResult = scrapeSingle(caseNumber)
                        now = datetime.datetime.now()
                        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
                        if caseResult!=None:
                            title=caseResult['title']
                            content=caseResult['content']
                            caseType = checkType("", content)
                            statusCode = getStatusCode(title)
                            if statusCode in [9, 10, 11, 15] and caseType == "":
                                caseType = "ApprovedUnknown"
                            if statusCode in [14] and caseType=="":
                                caseType = "OtherStatusUnknown"
                            query ="UPDATE " +rangeId+ " SET caseType = %s, statusCode = %s, lastFetched = %s WHERE CaseNumber = %s"
                            cursor.execute(query, (caseType, statusCode, dt_string, caseNumber))
                            cnx.commit()

            except:
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!EXCEPTIONNN")
                print(numOfTries)
                sleep(10)
                dailyScrape(rangeId)
    cursor.close()
    databaseClose(cnx)
    

def checkAndFillRange(rangeId):
    if not rangeLogTableExist(rangeId):
        createRangeLogTable(rangeId)
    cnx = databaseConnect("RangeLog")
    tableName = "R"+rangeId
    cursor = cnx.cursor()
    now = datetime.datetime.now()
   
    caseTypes = {"I-140":0,"I-765":0,"I-821":0,"I-131":0,"I-129":0,"I-539":0,"I-130":0,"I-90":0,"I-485":0,"N-400":0,"I-751":0, "I-824":0, "Approv":0, "OtherS":0}

    for caseType in caseTypes.keys():
        cnx2=databaseConnect("QueryableCases")
        cursor2=cnx2.cursor()    
        query="Select StatusCode from "+rangeId+" where CaseType=%s"
        cursor2.execute(query, (caseType,))
        
        statusCodesTups = cursor2.fetchall()
        cursor2.close()
        cnx2.close()

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
    databaseClose(cnx)






