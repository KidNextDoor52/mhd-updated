from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from app.db import db

def build_injury_risk_features(version="risk_v1", lookbacks=(7,28), now=None) -> int:
    """
    1) pull recent sessions, vitals, injuries
    2) compute rolling aggs per athlete
    3) convert nlp metadata (topics & sentiment) to numeric features
    4) upsert into 'features' with 'verstion'
    returns count written
    """

    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=max(lookbacks)+2)

    sess = list(db.sessions.find({"ts": {"$gte": since}}))
    vit = list(db.vitals.find({"ts": {"$gte": since}}))
    inj = list(db.injuries.find({"onset_date": {"$gte": since - timedelta(days=90)}}))

    if not sess: return 0

    sdf = pd.DataFrame(sess)
    sdf["ts"] = pd.to_datetime(sdf["ts"])
    sdf["date"] = sdf["ts"].dt.date

    # basic numeric features
    g = sdf.groupby(["athlete_id","date"]).agg({
        "work.volume":"sum",
        "work.intensity":"mean",
        "adherence":"mean",
        "nlp.sentiment":"mean"   # None will become NaN => fill later
    }).reset_index()
    g.columns = ["athlete_id","date","volume","intensity","adherence","sentiment"]

    # nlp topics count
    topic_rows=[]
    for s in sess:
        topics = (s.get("nlp",{}) or {}).get("topics",[])
        for t in topics:
            topic_rows.append({"athlete_id":s["athlete_id"], "date": pd.to_datetime(s["ts"]).date(), "topic":t})
    tdf = pd.DataFrame(topic_rows) if topic_rows else pd.DataFrame(columns=["athlete_id","date","topic"])

    out_docs=[]
    for aid, sub in g.groupby("athlete_id"):
        sub = sub.sort_values("date")
        sub = sub.set_index("date")

        # rolling windows
        r7 = sub.rolling(7, min_periods=1).agg({"volume":"sum", "intensity":"mean", "adherence":"mean", "sentiment":"mean"})
        r28 = sub.rolling(28, min_periods=1).agg({"volume":"sum"})

        #topic counts last 7d
        t7 = {}
        if not tdf.empty:
            tt = tdf[tdf["athlete_id"]==aid].groupby(["topic","date"]).size().unstack(fill_value=0).rolling(7, min_periods=1, axis=1).sum()
            # for each last date, take counts of a few common topics:
            common = ["knee","back","shoulder","fatigue","sleep","soreness"]
            latest_date = sub.index.max()
            for c in common:
                t7[f"nlp_topic_{c}_7d"] = float(tt.loc[c, latest_date]) if (c in tt.index and latest_date in tt.columns) else 0.0
        latest = sub.index.max()
        feat = {
            "age": None, #add athletes if you want
            "load_sum7": float(r7.loc[latest,"volume"]) if latest in r7.index else 0.0,
            "load_sum8": float(r28.loc[latest,"volume"]) if latest in r28.index else 0.0,
            "intensity_avg7": float(r7.loc[latest,"intensity"]) if latest in r7.index else 0.0,
            "adherence_avg7": float(r7.loc[latest,"adherence"]) if latest in r7.index else 0.0,
            "nlp_sentiment_avg7": float(r7.loc[latest,"sentiment"]) if latest in r7.index else 0.0,
            **t7
        }

        # prior injury in last 90d
        recent_inj = any((i["athlete_id"]==aid) for i in inj)
        feat["prior_injury_90d"] = 1 if recent_inj else 0

        out_docs.append({
            "athlete_id": aid,
            "ts": datetime.combine(latest, datetime.min.time(), tzinfo=timezone.utc),
            "version": version,
            "x": feat
        })

    if out_docs:
        for d in out_docs:
            db.features.update_one(
                {"athlete_id": d["athlete_id"], "ts": d["ts"], "version": version},
                {"$set": d},
                upsert=True
            )
    return len(out_docs)

