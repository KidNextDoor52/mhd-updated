from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timezone
from app.db import db
from app.auth import get_current_user
from app.utils.logger import log_activity

router = APIRouter(prefix="/profile", tags=["profile"])
templates = Jinja2Templates(directory="app/templates")
profile_col = db.profile

def _utcnow():
    return datetime.now(timezone.utc)

@router.get("", response_class=HTMLResponse)          # /profile
@router.get("/", response_class=HTMLResponse)         # /profile/
async def profile_page(request: Request, current_user: dict = Depends(get_current_user)):
    prof = profile_col.find_one({"username": current_user["username"]}) or {}
    return templates.TemplateResponse("profile.html", {"request": request, "user": current_user, "profile": prof})

@router.post("/update")
async def profile_update(
    request: Request,
    full_name: str = Form(""),
    email: str = Form(""),
    dob: str = Form(""),
    phone: str = Form(""),
    address: str = Form(""),
    emergency_name: str = Form(""),
    emergency_phone: str = Form(""),
    position: str = Form(""),
    team: str = Form(""),
    current_user: dict = Depends(get_current_user),
):
    payload = {
        "username": current_user["username"],
        "full_name": full_name,
        "email": email,
        "dob": dob,
        "phone": phone,
        "address": address,
        "emergency": {"name": emergency_name, "phone": emergency_phone},
        "sport_info": {"position": position, "team": team},
        "updated_at": _utcnow(),
    }
    profile_col.update_one({"username": current_user["username"]}, {"$set": payload}, upsert=True)
    log_activity(current_user["username"], "update_profile", {"fields": [k for k in payload.keys() if k != "username"]})
    return RedirectResponse("/profile?saved=1", status_code=303)
