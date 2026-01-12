# app/routes/models.py
from fastapi import APIRouter, HTTPException, Query, Depends
import os, json
import mlflow

from app.audit import log_event                       
from app.authz import get_current_user, require_role  

router = APIRouter(prefix="/models", tags=["models"])
DEPLOYED_PATH = "/app/.registry/deployed.json"  # kept if you still use it somewhere

@router.get("/current", dependencies=[Depends(require_role("trainer"))])
async def current(user = Depends(get_current_user)):
    # If you're now fully on Registry, you might instead return the current Production version
    client = mlflow.tracking.MlflowClient()
    name = os.getenv("MODEL_NAME", "mhd_logreg")
    versions = client.search_model_versions(f"name='{name}' and current_stage='Production'")
    if not versions:
        raise HTTPException(status_code=404, detail="No Production model")
    mv = max(versions, key=lambda v: int(v.version))
    await log_event(user.get("username"), "models_current", {"name": name, "version": mv.version})
    return {"name": name, "version": mv.version, "stage": "Production"}

@router.get("/compare", dependencies=[Depends(require_role("trainer"))])
async def compare(runs: list[str] = Query(..., description="repeat ?runs=<id>&runs=<id2>"), user = Depends(get_current_user)):
    client = mlflow.tracking.MlflowClient()
    out = []
    for r in runs:
        run = client.get_run(r)
        out.append({"run_id": r, "metrics": run.data.metrics, "params": run.data.params})
    await log_event(user.get("username"), "models_compare", {"runs": runs})
    return {"results": out}
