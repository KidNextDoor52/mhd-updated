import os
import uuid
import traceback
import datetime as dt

from app.db import db
from app.pipelines.orchestrator import run_training_job

jobs = db["jobs"]


def create_job(doc: dict) -> str:
    jid = str(uuid.uuid4())
    doc.update(
        {
            "_id": jid,
            "status": "queued",
            "created_at": dt.datetime.utcnow(),
        }
    )
    jobs.insert_one(doc)
    return jid


def mark(jid: str, **fields):
    jobs.update_one({"_id": jid}, {"$set": fields})


def _train_and_record(jid: str):
    """
    Runs the training job and updates job status.
    Intended to be called in a background task.
    """
    try:
        mark(jid, status="running", started_at=dt.datetime.utcnow())
        job_id = run_training_job()
        mark(
            jid,
            status="succeeded",
            finished_at=dt.datetime.utcnow(),
            result={"job_id": job_id},
        )
    except Exception as e:
        mark(
            jid,
            status="failed",
            finished_at=dt.datetime.utcnow(),
            error=str(e),
            traceback=traceback.format_exc(),
        )


def launch_train_job(background_tasks, payload: dict | None = None) -> str:
    """
    Create a job row and enqueue background run (using FastAPI BackgroundTasks).
    """
    jid = create_job({"type": "train", "params": payload or {}})
    background_tasks.add_task(_train_and_record, jid)
    return jid
