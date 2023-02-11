import pandas

secret = "82Husy82"
agentList = pandas.read_csv("agent-list.csv", header=0, usecols=["user_agent"])["user_agent"]