# simulate "deployement" by writiting a flag. later: use MLflow model registry
import json, os

REGISTRY_DIR = "/app/.registry"
os.makedirs(REGISTRY_DIR, exist_ok=True)

def promote (run_info: dict):
    with open(os.path.join(REGISTRY_DIR, "deployed.json"), "w") as f:
        json.dump(run_info, f)
    return True
