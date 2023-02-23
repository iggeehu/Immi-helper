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
    if not rangeLogTableExist(rangeId):
        cnx = databaseConnect("RangeLog")
        tableName = "R"+rangeId
        if cnx!=None:
            cursor = cnx.cursor()
            query = ("CREATE TABLE " + tableName + " LIKE RA001450")
            try:
                cursor.execute(query)
            except:
                print("Creating new table failed")
        else:
                 print("db connection failed")
        cnx.commit()
        cursor.close()
        cnx.close()




def populateRangeTable(rangeId):
    if not rangeTablePopulated(rangeId):
        cnx=databaseConnect("QueryableCases")
        if cnx!=None:
            case_stub = getCasePrefix(rangeId)+rangeId[1:7]
            cursor = cnx.cursor()
           
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
                cnx.commit()
        else:
            print("populating range table failed due to database Connection")
        
        cursor.close()
        databaseClose(cnx)
    else:
        return

def addToDistributionTable(rangeId):
 
        caseTypes = {"I-140":0,"I-765":0,"I-821":0,"I-131":0,"I-129":0,"I-539":0,
        "I-130":0,"I-90":0,"I-485":0,"N-400":0, "I-751":0, "I-824":0, "Approv":0, 
        "OtherS":0}
        cnx = databaseConnect("QueryableCases")
        cursor = cnx.cursor()
        
        for caseType in caseTypes.keys():

            query="Select count(*) from "+rangeId+ " where caseType=%s"
            cursor.execute(query, (caseType,))
           
            count = cursor.fetchone()[0]
            caseTypes[caseType]=count
        
        caseTypes["Invalid"]=0
        query = "Select count(*) from "+rangeId+ " where caseType is null"
        cursor.execute(query)
        caseTypes["Invalid"]=cursor.fetchone()[0]

        cursor.close()
        cnx.close()
     
        cnx2 = databaseConnect("TypeDistribution")
        cursor2=cnx2.cursor()
        query2="INSERT IGNORE INTO TypeDistribution (RangeId) values (%s) "
        cursor2.execute(query2,(rangeId,))
        cnx2.commit()
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
        cnx2.commit()
        cursor2.close()
        cnx2.close()







    
            
