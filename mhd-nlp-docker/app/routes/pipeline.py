from fastapi import APIRouter
from app.pipelines.orchestrator import run_training_job

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

@router.post("/train")
def trigger_training():
    jid = run_training_job()
    return {"status": "started", "job_id": jid}
