# app/routes/pipeline.py
from fastapi import APIRouter, Depends, Request

from app.auth import get_current_user
from app.authz import require_role
from app.audit import write_audit_event
from app.pipelines.orchestrator import run_training_job

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/train", dependencies=[Depends(require_role("trainer"))])
def trigger_training(request: Request, user=Depends(get_current_user)):
    jid = run_training_job()

    write_audit_event(
        tenant_id=user.get("org_id"),
        user_id=user.get("username") or user.get("_id"),
        action="pipeline_train_triggered",
        resource_type="pipeline_job",
        resource_id=str(jid),
        request=request,
    )

    return {"status": "started", "job_id": jid}
