from turtle import color
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure, show
from helpers.dbConnect import databaseConnect
from bokeh.embed import components
from constants import CASE_TYPES
from bokeh.models import DatetimeTickFormatter, Legend, LegendItem
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
        labels=["Case Received", "Active Review",  "RFE requested", "RFE received",
                "Interview Ready", "Interview Scheduled", "Approved", "Denied", "Other"]
        data = {"Approved":result[1], "Case Received":result[2], "date": dates, 
                "Active Review":result[3], "Denied":result[4], "RFE requested":result[5], 
                "Interview Scheduled":result[6], "Other":result[7], "Interview Ready":result[8], 
                "RFE received":result[9],
                }
        

        source = ColumnDataSource(data=data)
        
        dictOfGraphs[caseType] = figure(height=300, width=800,
           x_axis_type="datetime",
           background_fill_color="#efefef")
        dictOfGraphs[caseType].title.text = 'Number of Cases by Status, Over Time'
        
        for i in range(9):
            dictOfGraphs[caseType].line(dates, data[labels[i]], line_color=Category20_9[i], legend_label=labels[i])


        #give color to legend items
      
        
       
    return dictOfGraphs