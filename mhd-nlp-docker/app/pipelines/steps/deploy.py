# app/pipelines/steps/deploy.py
# Simulate "deployment" by writing a manifest. Also supports MLflow Model Registry.

import json
import os
from pathlib import Path

import mlflow

# Default to a writable location in Azure Container Apps.
# You can override via env var REGISTRY_DIR.
REGISTRY_DIR = os.getenv("REGISTRY_DIR", "/tmp/.registry")
MODEL_NAME = os.getenv("MODEL_NAME", "mhd_logreg")


def ensure_registry_dir() -> Path:
    """
    Ensure the registry directory exists and is writable.
    Returns the Path for convenience.
    """
    p = Path(REGISTRY_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def promote_to_registry(
    run_id: str,
    stage: str = "Production",
    archive_existing: bool = True,
):
    """
    Register the run's 'model' artifact and transition it to the given stage.
    """
    client = mlflow.tracking.MlflowClient()
    model_uri = f"runs:/{run_id}/model"

    # Ensure the registered model exists (idempotent)
    try:
        client.get_registered_model(MODEL_NAME)
    except Exception:
        # Some backends raise if not found; create is safe.
        client.create_registered_model(MODEL_NAME)

    mv = client.create_model_version(name=MODEL_NAME, source=model_uri, run_id=run_id)
    client.transition_model_version_stage(
        name=MODEL_NAME,
        version=mv.version,
        stage=stage,
        archive_existing_versions=archive_existing,
    )
    return {"name": MODEL_NAME, "version": mv.version, "stage": stage}


def promote(run_info: dict) -> bool:
    """
    "Deploy" by writing a manifest file to a writable registry dir.
    """
    registry_path = ensure_registry_dir()
    deployed_path = registry_path / "deployed.json"

    # Write atomically to reduce risk of partial writes
    tmp_path = deployed_path.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(run_info, f, indent=2)
    tmp_path.replace(deployed_path)

    return True
