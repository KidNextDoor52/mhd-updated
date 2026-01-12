from fastapi import APIRouter, BackgroundTasks, Depends
from rq.job import Job
from redis import Redis
import os

from app.jobs.queue import q, train_job
from app.audit import log_event
from app.auth import get_current_user
from app.authz import require_role

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/train-async", dependencies=[Depends(require_role("trainer"))])
async def train_async(user=Depends(get_current_user)):
    job = q.enqueue(train_job)
    log_event(
        user.get("username"),
        "train_async_enqueued",
        {"job_id": job.id},
    )
    return {"job_id": job.id, "status": "queued"}


@router.get("/status/{job_id}", dependencies=[Depends(require_role("trainer"))])
async def status(job_id: str, user=Depends(get_current_user)):
    r = Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))
    job = Job.fetch(job_id, connection=r)
    info = {"job_id": job.id, "status": job.get_status()}
    if job.is_finished:
        info["result"] = job.result
    if job.is_failed:
        info["exc_info"] = job.exc_info

    log_event(
        user.get("username"),
        "train_async_status",
        {"job_id": job.id, "status": info["status"]},
    )
    return info
