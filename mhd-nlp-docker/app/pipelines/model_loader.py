import os
import json
import mlflow

DEPLOYED_PATH = "/app/.registry/deployed.json"

def load_latest_or_production(model_name: str = None):
    """
    Unified loader:
    - If deployed.json exists, load that exact run
    - Else fallback to MLflow Registry Production stage
    """
    # 1 Manifest mode (your primary flow)
    if os.path.exists(DEPLOYED_PATH):
        with open(DEPLOYED_PATH) as f:
            manifest = json.load(f)

        
        model_uri = manifest.get("model_uri")
        run_id = manifest.get("run_id")

        model = mlflow.pyfunc.load_model(model_uri)
        return model, {
            "run_id": run_id,
            "model_uri": model_uri,
            "model_version": manifest.get("model_version")
        }
    
    #2 Registry fallback (if you clean registry only)
    if not model_name:
        raise ValueError("model_name required when no manifest exists.")
    
    uri = f"models:/{model_name}/Production"
    model = mlflow.pyfunc.load_model(uri)

    return model, {
        "run_id": "registry",
        "model_uri": uri,
        "model_version": "Production"
    }