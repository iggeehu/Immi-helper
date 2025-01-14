from constants import CASE_TYPES
from helpers.conversions import getCasePrefix
from random import sample

from helpers.dbConnect import DatabaseConnect, databaseConnect

def getAllRanges():
    with DatabaseConnect("TypeDistribution") as (cnx, cursor):
        query="Select rangeId from TypeDistribution"
        cursor.execute(query)
        list=[]
        listTups = cursor.fetchall()
        for tup in listTups:
            list.append(tup[0])
        return list

def getScannerPercentage(rangeId):
    with DatabaseConnect("QueryableCases") as (cnx, cursor):
        query="Select count(caseNumber) from "+rangeId+" where lastFetched > now() - interval 24 hour"
        cursor.execute(query)
        percentage=int(cursor.fetchone()[0]/5000*100)
        return percentage


    
def shuffledCasesList(rangeId):
    case_stub = getCasePrefix(rangeId)+rangeId[1:7]
    list=[]
    pool = range(5000, 9999) if rangeId[7]=='1' else range(0, 4999) 
    randomizedPool = sample(pool, 4999)
    for number in randomizedPool:
            list.append(case_stub + str(number))
            
    return list

def casesNotUpdatedToday(cursor, rangeId):
    query="Select CaseNumber from "+rangeId+" WHERE LastFetched < now() - interval 24 hour or LastFetched is null"
    # query="Select CaseNumber from "+rangeId+" WHERE caseType = ''"
    cursor.execute(query)
    listTups = cursor.fetchall()
    list=[]
    for tup in listTups:
        list.append(tup[0])
    return list

def casesNeverScanned(cursor, rangeId):
    query="Select CaseNumber from "+rangeId+" WHERE LastFetched is null"
    cursor.execute(query)
    listTups = cursor.fetchall()
    list=[]
    for tup in listTups:
        list.append(tup[0])
    return list

def NearApprovalAndFreshOrUnscanned(cursor, rangeId):
    query="Select CaseNumber from "+ rangeId +" where (StatusCode \
        in (2, 4, 5, 6, 8, 14) and DATE(LastFetched) != CURDATE()) \
            or (LastFetched is null)"
    cursor.execute(query)
    list=[]
    for tuple in cursor.fetchall():
        list.append(tuple[0])
    return list
  
def getCaseObj(cursor, rangeId, case_number):
    query="select * from "+rangeId + " where caseNumber = %s"
    cursor.execute(query, (case_number,))
    return cursor.fetchone()

def getStatusDataPerTypeDict(rangeId):
    dict = {}
    with DatabaseConnect("RangeLog") as (cnx, cursor):
        for caseType in CASE_TYPES:
            tableName = 'R' + rangeId
            query="select * from "+tableName+" where caseType = %s order by CollectionDate desc limit 1"
            cursor.execute(query, (caseType,))
            result = cursor.fetchone()
           
            statusCountSegmentTuple = result[3:14]
            
            count = 0
            for i in range(3, 14):
                count+=result[i]
            StatusCountSegmentTupleWithTotal=statusCountSegmentTuple+(count,)
            dict[caseType]=StatusCountSegmentTupleWithTotal
    return dict
