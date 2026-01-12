from datetime import datetime, timedelta, timezone
import pandas as pd
from app.db import db

def build_injury_labels(horizon_days=14) -> int:
    feats = list(db.features.find({"version":"risk_v1"}))
    if not feats: return 0
    fdf = pd.DataFrame(feats)
    fdf["ts"] = pd.to_datetime(fdf["ts"])

    inj = list(db.injuries.find())
    idf = pd.DataFrame(inj)
    if not idf.empty:
        idf["onset_date"] = pd.to_datetime(idf["onset_date"])
    else:
        idf = pd.DataFrame(columns=["athlete_id","onset_date"])

    c=0
    for _, row in fdf.iterrows():
        aid = row["athlete_id"]; ts = row["ts"]
        window_end = ts + timedelta(days=horizon_days)
        future_injury = not idf[(idf["athlete_id"]==aid) & (idf["onset_date"]>ts) & (idf["onset_date"]<=window_end)].empty
        lab = {
            "athlete_id": aid,
            "ts": ts,
            "horizon_days": horizon_days,
            "y": 1 if future_injury else 0
        }
        db.labels.update_one(
            {"athlete_id": aid, "ts": ts, "horizon_days": horizon_days},
            {"$set": lab},
            upsert = True
        )
        c+=1
    return c