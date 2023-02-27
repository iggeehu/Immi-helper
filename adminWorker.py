#!/py/bin/env python
from logging import raiseExceptions
from workers import batchScrape
import mysql.connector
from helpers.dbConnect import databaseConnect, databaseClose
from helpers.dbOperations import returnAllRanges
from customWorker import conn
from rq import Queue, Retry

def scrapeAll():
   
    rangesList = returnAllRanges()
    for range in rangesList:
        init = Queue('default', connection=conn)
        dailyScrapeJob = init.enqueue('workers.batchScrape', range, retry=Retry(max=10, interval=10),job_timeout='24h')