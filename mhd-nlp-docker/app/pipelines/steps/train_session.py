import os, mlflow
import pandas as pd, numpy as np
from scipy.stats import spearmanr
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from app.db import db

MODEL_NAME = os.getenv("SESSION_MODEL_NAME", "session_quality_rf")

def train_session(version="session_v1"):
    # build features akin to injury; here we assume feature.version=='session_v1' and labesl with coach_rating
    feats = list(db.features.find({"version": version}))
    if not feats: raise ValueError("No session features found")

    X = pd.DataFrame([f["x"] | {"athlete_id": f["athlete_id"], "ts": f["ts"]} for f in feats]).fillna(0.0)
    # label: coach_rating from sessions
    sess = pd.DataFrame(list(db.sessions.find({}, {"athlete_id":1,"ts":1,"coach_rating":1})))
    if sess.empty or sess["coach_rating"].isna().all():
        raise ValueError("No coach ratings present")
    sess["ts"] = pd.to_datetime(sess["ts"])
    ydf = sess.rename(columns={"coach_rating":"y"})

    df = X.merge(ydf, on=["athlete_id","ts"], how="inner").dropna(subset=["y"])
    feature_cols = [c for c in df.columns if c not in ("athlete_id","ts","y")]

    xtr, xte, ytr, yte = train_test_split(df[feature_cols], df["y"], test_size=0.2, random_state=42)
    model = RandomForestRegressor(n_estimators=200, random_state=42)

    with mlflow.start_run(run_name="sessions_quality"):
        mlflow.set_tag("use_case","session_quality")
        mlflow.log_param("feature_version", version)
        mlflow.sklearn.autolog(log_models=False)

        model.fit(xtr, ytr)
        pred = model.predict(xte)
        mae = mean_absolute_error(yte, pred)
        sp = float(spearmanr(yte, pred).correlation)

        mlflow.log_metric("val_mae", mae)
        mlflow.log_metric("val_spearman", sp)

        mlflow.sklearn.log_model(model, artifact_path="model", registered_model_name=MODEL_NAME)

        run_id = mlflow.active_run().info.run_id
        return {"run_id": run_id, "val_mae": float(mae), "val_spearman": sp, "model_uri": f"runs:/{run_id}/model"}


