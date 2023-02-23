import pandas
from dotenv import load_dotenv
import os



load_dotenv(".env")
dbPwd = os.environ("MYSQLPWD")

agentList = pandas.read_csv("agent-list.csv", header=0, usecols=["user_agent"])["user_agent"]