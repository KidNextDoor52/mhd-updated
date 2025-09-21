# app/services/sync.py
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from statistics import median
from typing import Optional, Dict, Any, List
from app.db import db

UTC = timezone.utc
def _utcnow(): return datetime.now(UTC)

# ---- snapshot ---------------------------------------------------------------
def rebuild_clinical_snapshot(username: str) -> Dict[str, Any]:
    """Builds a 1-document 'at-a-glance' summary."""
    snap: Dict[str, Any] = {
        "user": username,
        "generated_at": _utcnow(),
        "problems": [],
        "meds": [],
        "allergies": [],
        "last_vitals": {},
        "last_labs": [],
        "clearance": None,
    }

    med = db.medical_history.find_one({"username": username}) or {}
    if med:
        snap["allergies"] = [a.strip() for a in (med.get("allergies") or "").split(",") if a.strip()]
        snap["last_vitals"].update({
            "height_in": med.get("height_in"),
            "weight_lb": med.get("weight_lb"),
            "blood_type": med.get("blood_type"),
            "dob": med.get("dob"),
        })
        if "cleared" in med:
            snap["clearance"] = bool(med["cleared"])

    # latest weightroom metrics
    wr = db.weightroom.find_one({"username": username}) or {}
    if wr:
        snap["last_vitals"].update({
            "bench": wr.get("bench"),
            "squat": wr.get("squat"),
            "vertical": wr.get("vertical"),
            "forty_dash": wr.get("forty_dash"),
        })

    # wellness – pull last 7 days to compute headline signals
    last7 = list(db.metrics_daily.find({"user": username})
                 .sort("date", -1).limit(7))
    if last7:
        snap["wellness"] = {
            "rhr_bpm": last7[0].get("rhr_bpm"),
            "hrv_ms": last7[0].get("hrv_ms"),
            "sleep_total_min": last7[0].get("sleep_total_min"),
            "steps": last7[0].get("steps"),
        }

    db.clinical_snapshot.update_one(
        {"user": username},
        {"$set": snap},
        upsert=True,
    )
    return snap

# ---- simple rules engine ----------------------------------------------------
def run_risk_rules(username: str) -> List[Dict[str, Any]]:
    """Evaluate a few lightweight rules and store risk flags."""
    flags: List[Dict[str, Any]] = []
    def add(code: str, sev: str, msg: str, evidence: Dict[str, Any]):
        flags.append({"user": username, "date": _utcnow(), "code": code,
                      "severity": sev, "message": msg, "evidence": evidence})

    # HRV drop + low sleep
    days = list(db.metrics_daily.find({"user": username}).sort("date", -1).limit(21))
    if len(days) >= 14:
        recent = days[:7]
        prev   = days[7:21]
        rec_hrv = [d.get("hrv_ms") for d in recent if d.get("hrv_ms") is not None]
        prev_hrv = [d.get("hrv_ms") for d in prev if d.get("hrv_ms") is not None]
        if rec_hrv and prev_hrv:
            drop = (median(prev_hrv) - median(rec_hrv)) / max(median(prev_hrv), 1) * 100
            low_sleep = any((d.get("sleep_total_min") or 0) < 360 for d in recent)
            if drop > 20 and low_sleep:
                add("recovery_risk", "yellow",
                    "HRV down >20% and sleep <6h in last week.",
                    {"hrv_drop_pct": round(drop, 1)})

    # Not cleared
    mh = db.medical_history.find_one({"username": username})
    if mh and mh.get("cleared") is False:
        add("not_cleared", "red", "Athlete not cleared for participation.", {})

    # persist
    if flags:
        db.risk_flags.insert_many(flags)
    return flags