from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
from app.db import db

pred = db["risk_predictions"]   #{ts, athlete_id, p, model_run_id}
inj  = db["injuries"]           #{athlete_id, start_ts, end_ts?}
met  = db["model_daily_metrics"]# outputs

met.create_index([(day, 1)], unique=True)

def compute_precision_at_k(day: datetime, k_pct: float = 0.10):
    day = day.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    next_day = day + timedelta(days=1)

    # predictions generated on 'day' for horizon next 7d
    rows = list(pred.find({"ts": {"$gte": day, "$lt": next_day}}))
    if not rows:
        return None
    
    df = pd.DataFrame(rows)

    # label = did injury occur within next 7 days?

    horizon_end = next_day + timedelta(days=7)
    inj_map = set([r["athlete_id"] for r in inj.find(["star_ts": {"$gte": next_day, "$lt": horizon_end}])])
    df["label"] = df["athlete_id"].map(lambda a: 1 if a in inj_map else 0)

    k = max(1, int(np.ceil(len(df) * k_pct)))
    topk = df.sort_values("p", ascending=False).head(k)
    precision_at_k = topk["label"].mean() if k else 0.0

    met.update_one(
        {"day": day},
        {"$set": {
            "day": day,
            "n": int(len(df)),
            "k_pct": float(k_pct),
            "k": int(k),
            "precision_at_k": float(precision_at_k),

        }},
        upsert=True
    )
    return precision_at_k