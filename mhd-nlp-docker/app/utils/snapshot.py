from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

from app.db import db

# collections we’ll read/write
medical_history = db.medical_history
weightroom_col  = db.weightroom
metrics_daily   = db.metrics_daily  # optional – ok if empty/missing docs
snapshot_col    = db.clinical_snapshot

def _utcnow():
    return datetime.now(timezone.utc)

def _as_list(val: Any) -> List[str]:
    """
    Turn a comma/semicolon separated string or a scalar into a list of trimmed strings.
    If it's already a list, normalize its items; otherwise, return [] when empty.
    """
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    s = str(val).strip()
    if not s:
        return []
    # split on common delimiters
    parts = [p.strip() for p in s.replace(";", ",").split(",")]
    return [p for p in parts if p]

def _latest_metrics(username: str) -> Dict[str, Any]:
    """
    Fetch the most recent daily wellness metrics if present.
    Safe when the collection is empty.
    Expected fields (all optional): hrv_ms, sleep_total_min, steps, vo2max, rhr_bpm.
    """
    try:
        doc = metrics_daily.find_one({"user": username}, sort=[("date", -1)])
    except Exception:
        doc = None
    if not doc:
        return {}
    keep = ("hrv_ms", "sleep_total_min", "steps", "vo2max", "rhr_bpm", "source")
    return {k: doc.get(k) for k in keep if k in doc}

def rebuild_snapshot(username: str) -> Dict[str, Any]:
    """
    Compute a lightweight clinical snapshot for the user and upsert it into
    db.clinical_snapshot. This keeps your dashboard and mobile app fast.
    """
    med = medical_history.find_one({"username": username}) or {}
    wr  = weightroom_col.find_one({"username": username}) or {}
    wellness = _latest_metrics(username)

    # Core clinical bits
    allergies = _as_list(med.get("allergies"))
    last_vitals = {
        "height_in": med.get("height_in"),
        "weight_lb": med.get("weight_lb"),
        "blood_type": med.get("blood_type"),
        "dob": med.get("dob"),
        "name": med.get("name"),
    }

    # Strength / performance (from weightroom)
    strength = {
        "bench":       wr.get("bench"),
        "squat":       wr.get("squat"),
        "deadlift":    wr.get("deadlift"),
        "power_clean": wr.get("power_clean"),
        "vertical":    wr.get("vertical"),
        "forty_dash":  wr.get("forty_dash"),
    }

    snapshot_doc = {
        "username": username,
        "generated_at": _utcnow(),
        "allergies": allergies,
        "clearance": med.get("cleared"),          # True/False/None
        "injury_history": med.get("injury_history"),
        "last_vitals": last_vitals,
        "strength": strength,
        "wellness": wellness,
    }

    snapshot_col.update_one(
        {"username": username},
        {"$set": snapshot_doc},
        upsert=True,
    )
    return snapshot_doc
