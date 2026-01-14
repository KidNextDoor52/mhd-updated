# app/routes/pipeline_ingest.py
from fastapi import APIRouter, HTTPException, Query, Depends, Request
import hashlib
import pandas as pd
import mlflow

from app.storage.backend import get_bytes_raw
from app.pipelines.steps.train import train_basic
from app.auth import get_current_user
from app.authz import require_role
from app.audit import write_audit_event

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/train-from-blob", dependencies=[Depends(require_role("trainer"))])
async def train_from_blob(
    request: Request,
    key: str = Query(...),
    user=Depends(get_current_user),
):
    """
    Pull a CSV from raw storage, train a basic model, and return metrics.
    """
    try:
        b = get_bytes_raw(key)
    except Exception:
        raise HTTPException(status_code=404, detail="Object not found")

    data_sha256 = hashlib.sha256(b).hexdigest()

    try:
        df = pd.read_csv(pd.io.common.BytesIO(b))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

    with mlflow.start_run(run_name="csv-train") as run:
        mlflow.log_param("data_key", key)
        mlflow.log_param("data_sha256", data_sha256)

        metrics = train_basic(df)
        if isinstance(metrics, dict):
            metrics.setdefault("run_id", run.info.run_id)

    write_audit_event(
        tenant_id=user.get("org_id"),
        user_id=user.get("username") or user.get("_id"),
        action="pipeline_train_from_blob",
        resource_type="data_object",
        resource_id=key,
        extra={"data_sha256": data_sha256, "run_id": metrics.get("run_id") if isinstance(metrics, dict) else None},
        request=request,
    )

    return {"status": "trained", "metrics": metrics, "data_sha256": data_sha256}
