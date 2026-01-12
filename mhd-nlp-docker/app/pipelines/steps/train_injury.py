import os, mlflow
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score

from app.db import db

MODEL_NAME = os.getenv("INJURY_MODEL_NAME", "injury_risk_logreg")

def train_injury(version="risk_v1", horizon_days=14):
    feats = list(db.features.find({"version": version}))
    labs = list(db.labels.find({"horizon_days": horizon_days}))
    if not feats or not labs:
        raise ValueError("No features or labels found")
    
    x = pd.DataFrame([f["x"] | {"athlete_id": f["athlete_id"], "ts": f["ts"]} for f in feats])
    y = pd.DataFrame(labs)[["athlete_id","ts","y"]]

    # join on athlete_id+ts
    df = x.merge(y, on=["athlete_id","ts"], how="inner").fillna(0.0)
    feature_cols = [c for c in df.columns if c not in ("athlete_id","ts","y")]

    xtr, xte, ytr, yte = train_test_split(df[feature_cols], df["y"], test_size=0.2, random_state=42, stratify=df["y"])
    model = LogisticRegression(max_iter=200, class_weight="balanced")

    with mlflow.start_run(run_name="injury_risk"):
        mlflow.set_tag("use_case","injury_risk")
        mlflow.log_param("feature_verstion", version)
        mlflow.log_param("horizon_days", horizon_days)
        mlflow.sklearn.autolog(log_models=False)

        model.fit(xtr, ytr)
        proba = model.predict_proba(xte)[:,1]
        auc = roc_auc_score(yte, proba)
        pr  = average_precision_score(yte, proba)

        mlflow.log_metric("val_auc", auc)
        mlflow.log_metric("val_pr_auc", pr)

        # log the model artifact under folder "model"
        mlflow.sklearn.log_model(model, artifact_path="model", registered_model_name=os.getenv("MODEL_NAME","mhd_logreg"))

        run_id = mlflow.active_run().info.run_id
        return {"run_id": run_id, "val_auc": float(auc), "val_pr_auc": float(pr), "model_uri": f"runs:/{run_id}/model"}
