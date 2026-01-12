# app/pipelines/orchestrator.py
import os, uuid
import pandas as pd, numpy as np
import mlflow

from .steps.deid import deidentify
from .steps.quality import basic_schema_check, session_schema_check
from .steps.deploy import promote, promote_to_registry
from .steps.validate import validate_metrics
from .steps.train import train_basic

from app.features.session_v1 import build_session_dataset
from app.features.injury_risk import build_injury_risk_features
from app.labeling.injury_risk import build_injury_labels
from app.pipelines.steps.train_injury import train_injury
from app.pipelines.steps.train_session import train_session

mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
PROMOTE_AUC = float(os.getenv("PROMOTE_MIN_AUC", "0.75"))





def run_training_job() -> str:
    job_id = str(uuid.uuid4())
    X = pd.DataFrame({
        "age": np.random.randint(18, 80, 500),
        "bp":  np.random.normal(120, 15, 500),
        "hr":  np.random.normal(72, 10, 500),
    })
    y = ((X["age"] > 50) & (X["bp"] > 130)).astype(int)
    df = X.copy()
    df["target"] = y

    df = deidentify(df)
    checks = basic_schema_check(df)
    if not checks["ok"]:
        with mlflow.start_run(run_name="dq_failed"):
            mlflow.log_param("dq_failed", "true")
            mlflow.log_text("\n".join(checks["issues"]), "dq_issues.txt")
        raise ValueError(f"Data quality failed: {checks['issues']}")
    
    # -- clean categorical values ==
    def normalize_numeric(val):
        if isinstance(val, (float, int)):
            return val
        if isinstance(val, str):
            if val.endswith("+"):
                return float(val[:-1])
            if "-" in val:
                lo, hi = val.split("-")
                return (float(lo) + float(hi)) / 2.0
        return None

    df["age"] = df["age"].apply(normalize_numeric)
    df["bp"] = df["bp"].apply(normalize_numeric)
    df["hrj"] = df["hr"].apply(normalize_numeric)
    df = df.dropna()


    metrics = train_basic(df)
    if validate_metrics(metrics) and float(metrics.get("val_auc", 0.0)) >= PROMOTE_AUC:
        promote_to_registry(metrics["run_id"], stage="Production")
    promote({"metrics": metrics, "run_id": metrics["run_id"], "model_uri": metrics["model_uri"]})
    return job_id

def run_injury_risk_training():
    v = "risk_v1"
    n = build_injury_risk_features(version=v)
    l = build_injury_labels(horizon_days=14)
    metrics = train_injury(version=v, horizon_days=14)

    if validate_metrics(metrics) and metrics["val_auc"] >= PROMOTE_AUC:
        promote_to_registry(metrics["run_id"], stage="Production")
    promote({"metrics": metrics, "run_id": metrics["run_id"], "model_uri": metrics["model_uri"]})
    return {"features_built": n, "labels_built": l, **metrics}

def run_session_quality_training():
    metrics = train_session(version="session_v1")
    promote({"metrics": metrics, "run_id": metrics["run_id"], "model_uri": metrics["model_uri"]})
    return metrics
