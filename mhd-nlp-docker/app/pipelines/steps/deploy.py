# app/pipelines/steps/deploy.py
# Simulate "deployment" by writing a manifest. Also supports MLflow Model Registry.
import json, os
import mlflow

REGISTRY_DIR = "/app/.registry"
os.makedirs(REGISTRY_DIR, exist_ok=True)

MODEL_NAME = os.getenv("MODEL_NAME", "mhd_logreg")

def promote_to_registry(run_id: str, stage: str = "Production", archive_existing: bool = True):
    """
    Register the run's 'model' artifact and transition it to the given stage.
    """
    client = mlflow.tracking.MlflowClient()
    model_uri = f"runs:/{run_id}/model"

    # Ensure the registered model exists (idempotent)
    try:
        client.get_registered_model(MODEL_NAME)
    except Exception:
        client.create_registered_model(MODEL_NAME)

    mv = client.create_model_version(name=MODEL_NAME, source=model_uri, run_id=run_id)
    client.transition_model_version_stage(
        name=MODEL_NAME,
        version=mv.version,
        stage=stage,
        archive_existing_versions=archive_existing,
    )
    return {"name": MODEL_NAME, "version": mv.version, "stage": stage}

def promote(run_info: dict):
    with open(os.path.join(REGISTRY_DIR, "deployed.json"), "w") as f:
        json.dump(run_info, f)
    return True
