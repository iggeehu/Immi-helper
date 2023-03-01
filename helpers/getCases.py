from helpers.conversions import getCasePrefix
from random import sample

from helpers.dbConnect import databaseConnect

def getAllRanges():
    cnx = databaseConnect("TypeDistribution")
    cursor = cnx.cursor()
    query="Select rangeId from TypeDistribution"
    cursor.execute(query)
    list=[]
    listTups = cursor.fetchall()
    for tup in listTups:
        list.append(tup[0])
    return list
    
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
    query="Select CaseNumber from "+ rangeId +" where (StatusCode in (2, 4, 5, 6, 8, 14) and DATE(LastFetched) != CURDATE()) or (LastFetched is null)"
    cursor.execute(query)
    list=[]
    for tuple in cursor.fetchall():
        list.append(tuple[0])
    return list
  
def getCaseObj(cursor, rangeId, case_number):
    query="select * from "+rangeId + " where caseNumber = %s"
    cursor.execute(query, (case_number,))
    return cursor.fetchone()
    