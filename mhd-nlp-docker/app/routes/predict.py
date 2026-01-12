# app/routes/predict.py
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import time
import os
import json
import pandas as pd
import mlflow

from app.db import db
from app.auth import get_current_user
from app.authz import require_role
from app.schemas.predict import RiskRequest, SessionScoreRequest
from app.pipelines.model_loader import load_latest_or_production
from app.utils.audit import audit

router = APIRouter(prefix="/predict", tags=["predict"])
api_metrics = db["api_metrics"]
api_metrics.create_index("ts")

# ------------ Injury Risk ------------

@router.post("/risk")
@audit("predict.risk")
async def predict_risk(payload: RiskRequest,
                       user=Depends(require_role("viewer"))):
    # load injury-risk model
    model, meta = load_latest_or_production(model_name="injury_risk_logreg")

    df = pd.DataFrame([i.dict() for i in payload.items])
    feature_cols = df.columns.tolist()
    if df.empty:
        raise HTTPException(status_code=400, detail="No rows provided")

    if hasattr(model, "predict_proba"):
        scores = model.predict_proba(df[feature_cols])[:, 1]
    else:
        scores = model.predict(df[feature_cols])

    now = datetime.now(timezone.utc)
    docs, results = [], []
    for row, s in zip(payload.items, scores):
        s_float = float(s)
        results.append({
            "risk": s_float,
            "model_run_id": meta.get("run_id"),
            "model_version": meta.get("model_version"),
        })
        docs.append({
            "ts": now,
            "use_case": "injury_risk",
            "features": row.dict(),
            "score": s_float,
            "run_id": meta.get("run_id"),
            "model_version": meta.get("model_version"),
        })
    if docs:
        db["risk_predictions"].insert_many(docs)

    return {"predictions": results, "model_info": meta}


# ------------ Session Quality ------------

@router.post("/session_score")
@audit("predict.session_score")
async def predict_session_score(req: SessionScoreRequest,
                                user=Depends(require_role("viewer"))):
    t0 = time.perf_counter()
    model, meta = load_latest_or_production(model_name="mhd_session_score")
    df = pd.DataFrame([i.dict() for i in req.items])

    cols = [
        "sets", "reps", "rpe", "rest_s", "completed_pct",
        "nlp_fatigue", "nlp_pain_any", "nlp_sleep_poor",
        "nlp_mood_neg", "nlp_compliance_issues",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = 0.0
    X = df[cols]

    preds = model.predict(X) if hasattr(model, "predict") else model.predict_proba(X)[:, 1]
    latency_ms = (time.perf_counter() - t0) * 1000.0

    api_metrics.insert_one({
        "ts": datetime.now(timezone.utc),
        "endpoint": "/predict/session_score",
        "latency_ms": float(latency_ms),
        "n": len(df),
        "model_run_id": meta.get("run_id"),
        "model_uri": meta.get("model_uri"),
        "ok": True,
    })

    docs = []
    now = datetime.now(timezone.utc)
    for row, s in zip(req.items, preds):
        s_float = float(s)
        docs.append({
            "ts": now,
            "use_case": "session_quality",
            "features": row.dict(),
            "score": s_float,
            "run_id": meta.get("run_id"),
            "model_version": meta.get("model_version"),
        })
    if docs:
        db["session_scores"].insert_many(docs)

    return {
        "predictions": [float(x) for x in preds],
        "meta": meta,
    }
