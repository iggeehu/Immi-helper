
from secret import secret
import mysql.connector
from mysql.connector import errorcode

def databaseConnect(schema):
    try:
        cnx = mysql.connector.connect(user='admin', password=secret,
                                host='immigence.cor389u8xll2.us-east-1.rds.amazonaws.com',
                                database=schema)
        return cnx
    except mysql.connector.Error as err:
        print("Something went wrong: {}".format(err))

def databaseClose(cnx):
    cnx.close()