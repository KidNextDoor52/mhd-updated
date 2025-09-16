from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timezone

from app.db import db
from app.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")

# Collections (one source of truth)
uploads_col = db.uploads
medical_history_col = db.medical_history
equipment_col = db.equipment
training_col = db.training
weightroom_col = db.weightroom
activity_logs_col = db.activity_logs


def _ensure_aware_utc(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            if dt.endswith("Z"):
                dt = dt[:-1]
            return datetime.fromisoformat(dt).replace(tzinfo=timezone.utc)
        except Exception:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def humanize_time(dt):
    dt = _ensure_aware_utc(dt)
    if not dt:
        return "just now"
    now = datetime.now(timezone.utc)
    diff = now - dt
    s = int(diff.total_seconds())
    if s < 60:
        return "just now"
    m = s // 60
    if m < 60:
        return f"{m} min ago"
    h = m // 60
    if h < 24:
        return f"{h} hr ago"
    d = h // 24
    return f"{d} d ago"

def format_label(value: str) -> str:
    """Clean underscores and fix casing for display labels."""
    if not value:
        return "—"
    return value.replace("_", " ").title()

@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, current_user: dict = Depends(get_current_user)):
    username = current_user["username"]

    # Documents (from uploads)
    docs = list(uploads_col.find({"username": username}).sort("upload_date", -1).limit(10))
    doc_count = uploads_col.count_documents({"username": username})

    # Group by category (lowercase keys to match template)
    grouped_docs = {"medical": [], "performance": [], "equipment": []}
    for d in docs:
        for cat in (d.get("category") or []):
            k = (cat or "").strip().lower()
            if k in grouped_docs:
                grouped_docs[k].append(d)

    # Medical summary (single doc)
    medical = medical_history_col.find_one({"username": username}) or {}

    # Equipment (ensure items is a list)
    user_equipment = equipment_col.find_one({"username": username}) or {}
    if not isinstance(user_equipment.get("items"), list):
        user_equipment["items"] = []
    
    # Clean display values for equipment items
    for it in user_equipment["items"]:
        for key in ["category", "brand", "type", "size", "notes"]:
            if key in it:
                it[key] = format_label(it[key])
                
    # Training
    training_logs = list(training_col.find({"username": username}).sort("_id", -1).limit(5))
    training_count = training_col.count_documents({"username": username})

    # Weightroom
    weightroom_stats = weightroom_col.find_one({"username": username}) or {}

    # Activity
    activity = list(activity_logs_col.find({"user_id": username}).sort("_id", -1).limit(5))
    for log in activity:
        log["friendly_time"] = humanize_time(log.get("timestamp"))

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": current_user,
            "doc_count": doc_count,
            "recent_docs": docs,
            "grouped_docs": grouped_docs,
            "medical": medical,
            "equipment": user_equipment,
            "training_logs": training_logs,
            "training_count": training_count,
            "weightroom": weightroom_stats,
            "activity": activity,
        },
    )
