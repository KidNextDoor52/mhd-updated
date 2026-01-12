from fastapi import APIRouter, HTTPException, Query, Depends
import hashlib
import pandas as pd
import mlflow

from app.db.storage import get_bytes_raw
from app.pipelines.steps.train import train_basic
from app.pipelines.steps.validate import validate_metrics
from app.pipelines.steps.deploy import promote_to_registry
from app.auth import get_current_user
from app.authz import require_role

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/train-from-blob", dependencies=[Depends(require_role("trainer"))])
async def train_from_blob(
    key: str = Query(...),
    user=Depends(get_current_user),
):
    """
    Pull a CSV from raw storage (Azure Blob or S3), train a basic model, validate metrics,
    and if valid promote it to the registry.
    """
    try:
        b = get_bytes_raw(key)
    except Exception:
        raise HTTPException(status_code=404, detail="Blob/S3 object not found")

    data_sha256 = hashlib.sha256(b).hexdigest()

    try:
        df = pd.read_csv(pd.io.common.BytesIO(b))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

    with mlflow.start_run(run_name="csv-train") as run:
        mlflow.log_param("data_key", key)
        mlflow.log_param("data_sha256", data_sha256)

        metrics = train_basic(df)

        # Optional but helpful:
        # If train_basic doesn't include run_id/model_uri, set them here.
        if isinstance(metrics, dict):
            metrics.setdefault("run_id", run.info.run_id)
            # If your train_basic already logs model and returns model_uri, ignore.
            # metrics.setdefault("model_uri", "runs:/{}/model".format(run.info.run_id))

    if validate_metrics(metrics):
        promote_to_registry(
            {
                "metrics": metrics,
                "run_id": metrics.get("run_id"),
                "model_uri": metrics.get("model_uri"),
                "data_key": key,
                "data_sha256": data_sha256,
            }
        )

    return {"status": "trained", "metrics": metrics, "data_sha256": data_sha256}
