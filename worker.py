from redis import Redis
from rq import Worker

# Preload libraries
from distutils.log import error
from xmlrpc.client import DateTime
from helpers import scrapeSingle, databaseConnect, databaseClose, scrapeComplete, getCasePrefix, checkType, getStatusCode,caseInited, fetchedButInvalid, OneStepBeforeApprovalAndFresh
import numpy
from random import randint as rand, sample as sample
from time import sleep
from secret import secret, agentList
import mysql.connector
from mysql.connector import errorcode
import requests
import time
from bs4 import BeautifulSoup as bs
import random
from MySQLdb import _mysql
import datetime
from constants import SAMPLE_SIZE

# Provide the worker with the list of queues (str) to listen to.
w = Worker(['default'], connection=Redis())
w.work()
