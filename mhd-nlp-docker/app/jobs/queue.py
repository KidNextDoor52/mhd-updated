import os, json, traceback
from rq import Queue
from redis import Redis
from app.pipelines.orchestrator import run_training_job

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
redis = Redis.from_url(REDIS_URL)
q = Queue("mhd_jobs", connection=redis)

def train_job():
    #orchestrator does the real work
    try:
        jid = run_training_job()
        return {"ok": True, "training_job_id": jid}
    except Exception as e:
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}
    