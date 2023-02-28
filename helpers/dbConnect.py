
from secret import dbPwd
import mysql.connector
from mysql.connector import errorcode


def databaseConnect(schema):
    try:
        cnx = mysql.connector.connect(user='admin', password=dbPwd,
                                host='immigence.cor389u8xll2.us-east-1.rds.amazonaws.com',
                                database=schema)
        return cnx
    except mysql.connector.Error as err:
        print("Something went wrong: {}".format(err))


class DatabaseConnect:
    def __init__(self,name):
        self.name=name
    def __enter__(self):
        self.cnx = databaseConnect(self.name)
        self.cursor=self.cnx.cursor()
        return self.cnx, self.cursor
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cnx.commit()
        self.cursor.close()
        self.cnx.close()

    