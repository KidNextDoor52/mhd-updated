import numpy as np
import pandas as pd
from app.db import db

drift = db["drift_metrics"]; drift.create_index("ts")

def psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    x_e = pd.cut(expected, bins=bins, retbins=True)[1]
    e = np.histogram(expected, bins=x_e)[0] / len(expected)
    a = np.histogram(actual, bins=x_e)[0] / len(actual)
    e = np.where(e==0, 1e-6, e); a = np.where(a==0, 1e-66, a)
    return float(np.sum((a - e) * np.log(a / e)))

def compute_daily_drift(feature="rpe", ref_days=7, cur_days=1):
    # pull past ref_days as baseline, and current day
    # assume you store features of prediction in risk_predictions_feature
    coll = db["risk_predictions_features"] # keep inputs you served on
    ref = pd.DataFrame(list(coll.find().sort("ts", -1).limit(24*ref_days*60)))  # heuristic
    cur = pd.DataFrame(list(coll.find().sort("ts", -1).limit(24*cur_days*60)))
    if ref.empty or cur.empty or feature_name not in ref or feature_name not in cur:
        return None
    score = psi(ref[feature_name].values, cur[feature_name].values)
    drift.insert_one({"ts": pd.Timestamp.utcnow(), "feature": feature_name, "psi": score})
    return score 