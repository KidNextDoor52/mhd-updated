from __future__ import annotations
from datetime import datetime, timezone
from statistics import median
from typing import Dict, Any, List
from app.db import db
from app.utils.logger import log_activity

UTC = timezone.utc
def _utcnow(): return datetime.now(UTC)

def rebuild_clinical_snapshot(username: str) -> Dict[str, Any]:
    """
    Build a 1-document 'at-a-glance' clinical snapshot for a user.
    """
    snap: Dict[str, Any] = {
        "user": username,
        "generated_at": _utcnow(),
        "problems": [],
        "meds": [],
        "allergies": [],
        "last_vitals": {},
        "last_labs": [],
        "clearance": None,
        "wellness": {},
    }

    # medical_history
    med = db.medical_history.find_one({"username": username}) or {}
    if med:
        # allergies as list (CSV in source is ok)
        if med.get("allergies"):
            snap["allergies"] = [
                a.strip() for a in str(med["allergies"]).split(",") if a.strip()
            ]
        snap["last_vitals"].update({
            "height_in": med.get("height_in"),
            "weight_lb": med.get("weight_lb"),
            "blood_type": med.get("blood_type"),
            "dob": med.get("dob"),
        })
        if "cleared" in med:
            snap["clearance"] = bool(med["cleared"])

    # latest performance stats
    wr = db.weightroom.find_one({"username": username}) or {}
    if wr:
        snap["last_vitals"].update({
            "bench": wr.get("bench"),
            "squat": wr.get("squat"),
            "vertical": wr.get("vertical"),
            "forty_dash": wr.get("forty_dash"),
        })

    # wellness headline (take newest entry)
    last7 = list(
        db.metrics_daily.find({"user": username}).sort("date", -1).limit(7)
    )
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
    log_activity(user_id=username, action="rebuild_snapshot", metadata={})
    return snap

def run_risk_rules(username: str) -> List[Dict[str, Any]]:
    """
    Evaluate simple risk rules and persist risk_flags.
    """
    flags: List[Dict[str, Any]] = []

    def add(code: str, severity: str, message: str, evidence: Dict[str, Any]):
        flags.append({
            "user": username,
            "date": _utcnow(),
            "code": code,
            "severity": severity,
            "message": message,
            "evidence": evidence,
        })

    # Rule: HRV down >20% vs previous 14-day median AND any day sleep < 6h last week
    days = list(db.metrics_daily.find({"user": username}).sort("date", -1).limit(21))
    if len(days) >= 14:
        recent = days[:7]
        prev   = days[7:21]
        rec_hrv  = [d.get("hrv_ms") for d in recent if d.get("hrv_ms") is not None]
        prev_hrv = [d.get("hrv_ms") for d in prev   if d.get("hrv_ms") is not None]
        if rec_hrv and prev_hrv:
            prev_med = median(prev_hrv)
            rec_med  = median(rec_hrv)
            drop_pct = (prev_med - rec_med) / max(prev_med, 1) * 100
            low_sleep = any((d.get("sleep_total_min") or 0) < 360 for d in recent)
            if drop_pct > 20 and low_sleep:
                add("recovery_risk", "yellow",
                    "HRV down >20% and sleep <6h in last week.",
                    {"hrv_drop_pct": round(drop_pct, 1), "prev_med": prev_med, "rec_med": rec_med})

    # Rule: Not medically cleared
    mh = db.medical_history.find_one({"username": username})
    if mh and mh.get("cleared") is False:
        add("not_cleared", "red", "Athlete not cleared for participation.", {})

    if flags:
        db.risk_flags.insert_many(flags)
        log_activity(user_id=username, action="risk_flags_created", metadata={"count": len(flags)})
    return flags
