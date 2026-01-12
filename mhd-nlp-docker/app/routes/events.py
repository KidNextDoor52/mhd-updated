# app/routes/events.py
from fastapi import APIRouter, Depends, Body
from datetime import datetime, timezone
from typing import Optional
from app.auth import get_current_user
from app.db import db
from app.services.sync import rebuild_clinical_snapshot, run_risk_rules

UTC = timezone.utc
router = APIRouter(prefix="/api", tags=["events"])

@router.get("/events")
def list_events(limit: int = 100, current_user: dict = Depends(get_current_user)):
    user = current_user["username"]
    evs = list(db.events.find({"user": user}).sort("date", -1).limit(limit))
    return {"events": evs}

#  training room record 
@router.post("/training")
def add_training(
    injury: Optional[str] = Body(None),
    details: Optional[str] = Body(None),
    current_user: dict = Depends(get_current_user),
):
    user = current_user["username"]
    doc = {"username": user, "injury": injury, "details": details, "created_at": datetime.now(UTC)}
    db.training.insert_one(doc)
    db.events.insert_one({
        "user": user, "type": "training", "date": datetime.now(UTC),
        "source": "web", "summary": f"Training log: {injury or 'note'}", "tags": ["training"]
    })
    rebuild_clinical_snapshot(user)
    run_risk_rules(user)
    return {"ok": True}
