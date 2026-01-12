from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import mlflow


import csv
import io
import os

from fastapi import APIRouter, Depends, Request, HTTPException, Body, status
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.scripts.seed_demo_data import seed_predictions_and_forms

from app.db import db
from app.authz import require_role

router = APIRouter(prefix="/trainer", tags=["trainer"])
templates = Jinja2Templates(directory="app/templates")

UTC = timezone.utc

predictions = db["predictions"]
sessions_coll = db["sessions"]
forms_coll = db["forms"]  # adjust if your medical forms collection name differs
clearance_coll = db["clearance"]  # NEW: overrides for “cleared” athletes

ML_MODEL_VERSION = os.getenv("ML_MODEL_VERSION", "v1")
ML_MODEL_NAME = os.getenv("ML_MODEL_NAME", "InjuryRiskNet")

@router.post("/mlflow/train", response_class=JSONResponse)
def trainer_trigger_mlflow_run(user=Depends(require_role("trainer"))):

    # Configure MLflow tracking (match your docker-compose) 
    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment("mhd_injury_risk")

    # start an MLflow run
    with mlflow.start_run() as run:
        mlflow.log_param("triggered_by", user["username"])
        mlflow.log_param("timestamp", datetime.utcnow().isoformat())
        mlflow.log_metric("demo_accuracy", 0.87) #example metric
        mlflow.log_metric("demo_loss", 0.15)

        # Dummy artifact
        with open("/tmp/sample_artifact.txt", "w") as f:
            f.write("Demo model run triggered from trainer dashboard.")
        mlflow.log_artifact("/tmp/sample_artifact.txt")

        run_id = run.info.run_id
        experiment_id = run.info.experiment_id

    return {
        "status": "ok",
        "message": "MLflow run started",
        "run_id": run_id,
        "experiment_id": experiment_id,
        "mlflow_uri": "http://localhost:5001" 
    }

def _bucket_risk(items: List[Dict[str, Any]]):
    """Split risk predictions into high / med / low by score."""
    high, med, low = [], [], []
    for p in items:
        s = float(p.get("score", 0.0))
        if s >= 0.8:
            high.append(p)
        elif s >= 0.5:
            med.append(p)
        else:
            low.append(p)
    return high, med, low


def _top_per_athlete(items: List[Dict[str, Any]]):
    """Keep the highest-risk entry per athlete."""
    best_by_athlete: Dict[str, Dict[str, Any]] = {}
    for p in items:
        aid = p.get("athlete_id") or "unknown"
        s = float(p.get("score", 0.0))
        if aid not in best_by_athlete or s > float(best_by_athlete[aid].get("score", 0.0)):
            best_by_athlete[aid] = p
    return list(best_by_athlete.values())


def _compute_risk_drift(now: datetime) -> Dict[str, Any]:
    """
    Naive drift: compare average risk score in the last 7 days
    vs. the previous 7-day window.
    """
    recent_start = now - timedelta(days=7)
    prev_start = now - timedelta(days=14)

    recent = list(
        predictions.find(
            {
                "use_case": "injury_risk",
                "ts": {"$gte": recent_start, "$lte": now},
            }
        ).limit(2000)
    )
    prev = list(
        predictions.find(
            {
                "use_case": "injury_risk",
                "ts": {"$gte": prev_start, "$lt": recent_start},
            }
        ).limit(2000)
    )

    def avg_score(docs: List[Dict[str, Any]]) -> float:
        if not docs:
            return 0.0
        return sum(float(d.get("score", 0.0)) for d in docs) / len(docs)

    recent_avg = avg_score(recent)
    prev_avg = avg_score(prev)
    delta = recent_avg - prev_avg

    return {
        "recent_avg": recent_avg,
        "prev_avg": prev_avg,
        "delta": delta,
        "direction": "up" if delta > 0.01 else "down" if delta < -0.01 else "flat",
        "recent_count": len(recent),
        "prev_count": len(prev),
    }


@router.get("/dashboard", response_class=HTMLResponse)
def trainer_dashboard(
    request: Request,
    user=Depends(require_role("trainer")),  # trainer OR admin
):
    now = datetime.now(UTC)
    since = now - timedelta(days=7)

    # ---- Injury risk predictions (last 7 days) ----
    risk_cursor = (
        predictions.find(
            {
                "use_case": "injury_risk",
                "ts": {"$gte": since},
            }
        )
        .sort("score", -1)
        .limit(500)
    )
    risk_preds = list(risk_cursor)

    risk_high, risk_med, risk_low = _bucket_risk(risk_preds)
    top_high = _top_per_athlete(risk_high)  # one best entry per athlete

    risk_total = max(len(risk_preds), 1)
    risk_counts = {
        "high": len(risk_high),
        "med": len(risk_med),
        "low": len(risk_low),
    }
    risk_pct = {
        "high": (risk_counts["high"] / risk_total) * 100.0,
        "med":  (risk_counts["med"]  / risk_total) * 100.0,
        "low":  (risk_counts["low"]  / risk_total) * 100.0,
    }

    # Live high-risk list (most recent 25 high-risk predictions)
    live_high = list(
        predictions.find(
            {
                "use_case": "injury_risk",
                "score": {"$gte": 0.8},
                "ts": {"$gte": since},
            }
        )
        .sort("ts", -1)
        .limit(25)
    )

    # ---- Session quality predictions (last 7 days) ----
    sess_cursor = (
        predictions.find(
            {
                "use_case": "session_quality",
                "ts": {"$gte": since},
            }
        )
        .sort("ts", -1)
        .limit(500)
    )
    session_preds = list(sess_cursor)

    avg_session_score = None
    if session_preds:
        scores = [float(s.get("score", 0.0)) for s in session_preds]
        if scores:
            avg_session_score = sum(scores) / len(scores)

    # ---- Active clearance overrides (NEW) ----
    active_clearance_docs = list(
        clearance_coll.find({"cleared_until": {"$gte": now}})
    )
    cleared_ids = {doc.get("athlete_id") for doc in active_clearance_docs if doc.get("athlete_id")}

    # ---- Needs Clearance (high risk OR recent injury, minus cleared ids) ----
    needs_query = {
        "use_case": "injury_risk",
        "ts": {"$gte": since},
        "$or": [
            {"score": {"$gte": 0.8}},
            {"meta.recent_injury_flag": True},
        ],
    }
    if cleared_ids:
        needs_query["athlete_id"] = {"$nin": list(cleared_ids)}

    needs_clearance = list(
        predictions.find(needs_query)
        .sort("score", -1)
        .limit(20)
    )

    # ---- Pending medical forms ----
    pending_forms = list(
        forms_coll.find(
            {"status": {"$in": ["pending", "in_review"]}}
        )
        .sort("created_at", -1)
        .limit(15)
    )

    # ---- Model health / drift ----
    drift = _compute_risk_drift(now)

    alerts: List[str] = []
    if risk_counts["high"] >= 5:
        alerts.append(f"{risk_counts['high']} athletes in HIGH risk bucket.")
    if len(needs_clearance) > 0:
        alerts.append(f"{len(needs_clearance)} athletes require clearance.")
    if drift["direction"] == "up" and abs(drift["delta"]) >= 0.1:
        alerts.append(
            "Average injury risk score increased vs. last week "
            f"(Δ={drift['delta']:.2f})."
        )

    # ---- Model metadata for UI card ----
    model_meta = {
        "name": ML_MODEL_NAME,
        "version": ML_MODEL_VERSION,
        "last_trained_at": now - timedelta(days=2),
        "drift_flag": drift["direction"] == "up" and abs(drift["delta"]) >= 0.1,
    }

    # ---- High-level KPIs for analytic tiles ----
    total_athletes_tracked = len({p.get("athlete_id") for p in risk_preds if p.get("athlete_id")})
    total_predictions_week = len(risk_preds)
    high_risk_count = risk_counts["high"]
    needs_clearance_count = len(needs_clearance)
    pending_forms_count = len(pending_forms)

    # risk drift already computed as `drift`
    drift_delta = drift["delta"]
    drift_direction = drift["direction"]

    kpis = {
        "total_athletes": total_athletes_tracked,
        "total_predictions": total_predictions_week,
        "high_risk": high_risk_count,
        "needs_clearance": needs_clearance_count,
        "pending_forms": pending_forms_count,
        "avg_session_score": avg_session_score,
        "drift_delta": drift_delta,
        "drift_direction": drift_direction,
    }

    return templates.TemplateResponse(
        "trainer_dashboard.html",
        {
            "request": request,
            "user": user,
            "now": now,
            "risk_window_days": 7,
            "session_window_days": 7,
            "risk_high": risk_high,
            "risk_med": risk_med,
            "risk_low": risk_low,
            "risk_counts": risk_counts,
            "risk_pct": risk_pct,
            "top_high": top_high,
            "live_high": live_high,
            "sessions": session_preds,
            "avg_session_score": avg_session_score,
            "needs_clearance": needs_clearance,
            "pending_forms": pending_forms,
            "model_name": ML_MODEL_NAME,
            "model_version": ML_MODEL_VERSION,
            "drift": drift,
            "alerts": alerts,
            "model_meta": model_meta, # 👈 THIS LINE MAKES IT VISIBLE IN THE TEMPLATE
            "kpis": kpis,
        },
    )

@router.get("/athlete/{athlete_id}", response_class=JSONResponse)
def athlete_detail(
    athlete_id: str,
    user=Depends(require_role("trainer")),
):
    if not athlete_id:
        raise HTTPException(status_code=400, detail="Missing athlete_id")

    since = datetime.now(UTC) - timedelta(days=30)

    risk_docs = list(
        predictions.find(
            {
                "use_case": "injury_risk",
                "athlete_id": athlete_id,
                "ts": {"$gte": since},
            }
        )
        .sort("ts", -1)
        .limit(20)
    )

    session_docs = list(
        predictions.find(
            {
                "use_case": "session_quality",
                "athlete_id": athlete_id,
                "ts": {"$gte": since},
            }
        )
        .sort("ts", -1)
        .limit(20)
    )

    notes_docs = list(
        sessions_coll.find(
            {
                "athlete_id": athlete_id,
                "ts": {"$gte": since},
            }
        )
        .sort("ts", -1)
        .limit(10)
    )

    def _strip_id(doc: Dict[str, Any]) -> Dict[str, Any]:
        d = dict(doc)
        if "_id" in d:
            d["_id"] = str(d["_id"])
        return d

    return {
        "athlete_id": athlete_id,
        "injury_risk": [_strip_id(d) for d in risk_docs],
        "sessions": [_strip_id(d) for d in session_docs],
        "notes": [_strip_id(d) for d in notes_docs],
    }

@router.post("/demo/generate", status_code=status.HTTP_204_NO_CONTENT)
def trainer_generate_role(
    user=Depends(require_role("trainer")),
):
    
    # Re-run only the predictions/forms part of your seed script
    seed_predictions_and_forms()
    return 

@router.post("/clear/{athlete_id}", response_class=JSONResponse)
def clear_athlete(
    athlete_id: str,
    payload: dict = Body(None),
    user=Depends(require_role("trainer")),
):
    """
    Mark an athlete as 'cleared' for some days.
    This hides them from the Needs Clearance widget.
    """
    if not athlete_id:
        raise HTTPException(status_code=400, detail="Missing athlete_id")

    reason = (payload or {}).get("reason") or "trainer cleared"
    days = int((payload or {}).get("days") or 7)

    now = datetime.now(UTC)
    cleared_until = now + timedelta(days=days)

    clearance_coll.update_one(
        {"athlete_id": athlete_id},
        {
            "$set": {
                "athlete_id": athlete_id,
                "cleared_until": cleared_until,
                "reason": reason,
                "updated_at": now,
                "updated_by": user.get("username"),
            }
        },
        upsert=True,
    )

    return {
        "status": "ok",
        "athlete_id": athlete_id,
        "cleared_until": cleared_until.isoformat(),
    }
