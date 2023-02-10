import pandas

secret = "82@*Pelletier"
agentList = pandas.read_csv("agent-list.csv", header=0, usecols=["user_agent"])["user_agent"]