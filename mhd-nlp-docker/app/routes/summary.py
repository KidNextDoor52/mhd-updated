from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.db import db
from app.services.sync import rebuild_clinical_snapshot

router = APIRouter(prefix="/api", tags=["summary"])

@router.get("/summary")
def get_summary(current_user: dict = Depends(get_current_user)):
    user = current_user["username"]
    snap = db.clinical_snapshot.find_one({"user": user})
    if not snap:
        snap = rebuild_clinical_snapshot(user)
    last7 = list(db.metrics_daily.find({"user": user}).sort("date", -1).limit(7))
    flags = list(db.risk_flags.find({"user": user}).sort("date", -1).limit(5))
    return {"snapshot": snap, "metrics_last7": last7, "flags": flags}
