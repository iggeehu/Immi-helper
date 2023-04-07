from customWorker import conn
from rq import Queue, Worker
from redis import Redis

# conn = Redis()

def getWorkerBannerText():
    str="Scanning cases: "
    base=str
    workers=Worker.all(connection=conn)
    for worker in workers:
        if(worker.get_current_job_id()!=None):
            str+=worker.get_current_job_id()+" "

    if str==base:
        str += "none being scanned currently"
    return str