from fastapi import APIRouter, Depends
from app.authz import require_role
from datetime import datetime, timedelta, timezone
from app.db import db

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/secure-metrics")
async def secure_metrics(user=Depends(require_role("admin"))):
    coll = db["api_metrics"]
    docs = list(coll.find().sort("ts", -1).limit(500))
    return {"count": len(docs), "items": docs}


@router.get("/risk/summary")
async def risk_summary(user=Depends(require_role("trainer"))):
    today = datetime.now(timezone.utc).date().isoformat()
    agg = (
        db.metric_aggregates.find_one({"date": today, "use_case": "injury_risk"}) or {}
    )
    buckets = agg.get("risk_buckets", {"low": 0, "medium": 0, "high": 0})

    trend = []
    for d in range(7):
        day = (datetime.now(timezone.utc) - timedelta(days=6 - d)).date().isoformat()
        a = (
            db.metric_aggregates.find_one(
                {"date": day, "use_case": "injury_risk"}
            )
            or {}
        )
        trend.append(
            {
                "day": d,
                "high_count": (a.get("risk_buckets") or {}).get("high", 0),
            }
        )

    return {"buckets": buckets, "trend": trend}


@router.get("/session/summary")
async def session_summary(user=Depends(require_role("trainer"))):
    since = datetime.now(timezone.utc) - timedelta(days=1)
    preds = list(
        db.predictions.find(
            {"use_case": "session_quality", "ts": {"$gte": since}}
        )
    )
    bins = [0, 1, 2, 3, 4, 5]
    counts = {k: 0 for k in bins}
    for p in preds:
        k = round(min(5, max(0, p["score"])))
        counts[k] += 1
    return {"score_hist": counts}
