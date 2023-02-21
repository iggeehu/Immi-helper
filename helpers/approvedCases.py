
from helpers.dbOperations import databaseConnect, databaseClose, scrapeSingle, createRangeLogTable
from helpers.getCases import casesNotUpdatedToday, NearApprovalAndFreshOrUnscanned, casesNeverScanned
from helpers.conversions import getStatusCode
from helpers.checks import checkType, isLogUpdatedToday, rangeLogTableExist

from random import randint as rand, sample as sample
from time import sleep
import datetime
from constants import SAMPLE_SIZE, CASE_TYPES

def getApprovedCasesToday():
    cnx = databaseConnect("ApprovedCasesToday")
    cursor=cnx.cursor()
    todayApprovalsByType = {}
    for caseType in CASE_TYPES:
        query="select caseNumber from ApprovedCasesToday where ApprovalTime < now() - interval 24 hour \
              and caseType = %s"
        cursor.execute(query, (caseType,))
        result = cursor.fetchall()
        if result == None or len(result)==0:
            continue
        resultAsList = []
        for tup in result:
            resultAsList.append(tup[0])
        todayApprovalsByType[caseType] = resultAsList
    return todayApprovalsByType
