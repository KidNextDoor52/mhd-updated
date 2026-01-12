from datetime import datetime, timedelta, timezone
from app.db import db
import numpy as np

def aggregate_datily():
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    preds = list(db.predictions.find({"ts": {"$gte": day_start}}))
    if not preds: return

    # risk buckets
    risk = [p["score"] for p in preds if p["use_case"]=="injury_risk"]
    low = sum(1 for r in risk if r<0.33); med = sum(1 for r in risk if 0.33<=r<0.66); high = sum(1 for r in risk if r>=0.66)

    # precision@K (requires labels - you can compute yesterday's P@10 retrosprectively)
    # For now, simple placeholder:
    precision_at_10 = None

    doc = {
        "date": day_start.date().isoformat(),
        "use_case": "injury_risk",
        "risk_buckets": {"low":low,"medium":med,"high":high},
        "topk": {"k":10, "precision": precision_at_10},
        "latency_ms_avg": None,
        "error_rate": 0.0
    }
    db.metric_aggregates.update_one(
        {"date": doc["date"], "use_case":"injury_risk"},
        {"$set": doc}, upsert=True
    )