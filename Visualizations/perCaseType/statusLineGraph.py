from bokeh.models import ColumnDataSource
from bokeh.plotting import figure, show
from helpers.dbConnect import databaseConnect
from bokeh.embed import components
from constants import CASE_TYPES
from bokeh.models import DatetimeTickFormatter
import numpy as np
import pandas as pd
from bokeh.palettes import Category20_9

def getStatusDataPerType(rangeId, caseType):
    cnx = databaseConnect("RangeLog")
    cursor = cnx.cursor()
    tableName = "R"+rangeId
    query = "Select * from "+tableName +" where caseType = %s"
    cursor.execute(query, (caseType,))
    result = cursor.fetchall()
    collectionDates = []
    approved = []
    received = []
    activeReview =[]
    denied = []
    RFEreq = []
    IntSched = []
    Other =[]
    IntReady=[]
    RFErec = []
    for tup in result:
        collectionDates.append(tup[1])
        approved.append(tup[3])
        received.append(tup[4])
        activeReview.append(tup[5])
        denied.append(tup[6])
        RFEreq.append(tup[7])
        IntSched.append(tup[8])
        Other.append(tup[9])
        IntReady.append(tup[(10)])
        RFErec.append(tup[11])
    return [collectionDates, approved,received,activeReview,denied,RFEreq, IntSched, Other,IntReady,RFErec]



def outputStatusLineGraph(rangeId):
    dictOfGraphs = {}
    
    for caseType in CASE_TYPES:    
        result = getStatusDataPerType(rangeId, caseType)
        
       
        dates = pd.to_datetime(result[0])
        data = {"approved":result[1], "received":result[2], "date": dates, "activeReview":result[3], 
        "denied":result[4], "RFEreq":result[5], "IntSched":result[6], "Other":result[7], "IntReady":result[8], "RFErec":result[9]}

        source = ColumnDataSource(data=data)
        
        dictOfGraphs[caseType] = figure(height=300, width=800,
           x_axis_type="datetime",
           background_fill_color="#efefef")
        dictOfGraphs[caseType].title.text = 'Number of Cases by Status, Over Time'
  
  
        dictOfGraphs[caseType].vline_stack(["approved", "received", "activeReview", "denied", 
        "RFEreq", "IntSched", "Other", "IntReady", "RFErec"], color=Category20_9, x="date", source=source)


       
    return dictOfGraphs