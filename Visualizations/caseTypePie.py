

import pandas as pd
from bokeh.embed import components
from bokeh.palettes import Category20c
from bokeh.plotting import figure, show
from bokeh.transform import cumsum
from bokeh.models import (ColumnDataSource, DataTable, DateFormatter, TableColumn)
from bokeh.palettes import Bright7

from helpers.dbConnect import databaseConnect


def getDistributionData(rangeId):
    cnx = databaseConnect("TypeDistribution")
    cursor = cnx.cursor()
    query = "Select * from TypeDistribution where RangeId =%s"
    cursor.execute(query, (rangeId,))

    result = {}
    listOfValues = list(cursor.fetchone()[1:])
    listOfKeys = ["I485", "I765", "I129", "I130", "N400", "I539", 
    "I131", "I821", "Approved Unknown", "I140", "I90", "I824", "I751", "Invalid", "Other Unknown"]

    while len(listOfValues)!=0:
        value = listOfValues.pop()
        if value==0:
            listOfKeys.pop()
            continue
        result[listOfKeys.pop()]=value

    cursor.close()
    cnx.close()
    return result

def outputPlot(rangeId):
    result = getDistributionData(rangeId)
    keys=list(result.keys())
    values=list(result.values())
  

    sorted_keys = sorted(keys, key=lambda x: values[keys.index(x)])

    p = figure(x_range=sorted_keys, height=350, title="Number Per Case Type",
           toolbar_location=None, tools="")
    p.vbar(x=keys, top=values, width=0.9)
    p.xgrid.grid_line_color = None
    p.y_range.start = 0


    columns = [
            TableColumn(field="keys", title="Case Type"),
            TableColumn(field="values", title="Number"),
        ]
    
    source = ColumnDataSource(data=dict(keys=keys, values=values))
    data_table = DataTable(source=source, columns=columns, width=400, height=280, sortable=True)

    # script, div = 
    return (p, data_table)
