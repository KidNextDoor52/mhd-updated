# app/routes/pipeline_async.py
from fastapi import APIRouter, Depends, HTTPException, Request
import os
import uuid

from app.auth import get_current_user
from app.authz import require_role
from app.audit import write_audit_event

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/train-async", dependencies=[Depends(require_role("trainer"))])
async def train_async(request: Request, user=Depends(get_current_user)):
    """
    Placeholder async training enqueue.
    If/when you wire RQ or Azure Service Bus, replace this.
    """
    job_id = str(uuid.uuid4())

    write_audit_event(
        tenant_id=user.get("org_id"),
        user_id=user.get("username") or user.get("_id"),
        action="train_async_enqueued",
        resource_type="pipeline_job",
        resource_id=job_id,
        request=request,
    )

    return {"job_id": job_id, "status": "queued"}


@router.get("/status/{job_id}", dependencies=[Depends(require_role("trainer"))])
async def status(job_id: str, request: Request, user=Depends(get_current_user)):
    """
    Placeholder status endpoint.
    """
    write_audit_event(
        tenant_id=user.get("org_id"),
        user_id=user.get("username") or user.get("_id"),
        action="train_async_status_checked",
        resource_type="pipeline_job",
        resource_id=job_id,
        request=request,
    )

    return {"job_id": job_id, "status": "unknown (placeholder)"}
