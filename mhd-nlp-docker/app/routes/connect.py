# app/routes/connect.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from datetime import datetime, timezone
from app.auth import get_current_user
from app.db import db

router = APIRouter(prefix="/connect", tags=["connect"])
UTC = timezone.utc

@router.get("/{provider}")
def start_connect(provider: str, request: Request, current_user: dict = Depends(get_current_user)):
    # TODO: build provider-specific redirect URLs
    # For now, just mark a placeholder connection row.
    db.connections.update_one(
        {"user": current_user["username"], "provider": provider},
        {"$setOnInsert": {"status": "pending", "created_at": datetime.now(UTC)},
         "$set": {"updated_at": datetime.now(UTC)}},
        upsert=True)
    # redirect to a placeholder info page
    return RedirectResponse(f"/connect/{provider}/callback?ok=1", status_code=303)

@router.get("/{provider}/callback", response_class=HTMLResponse)
def finish_connect(provider: str, request: Request, current_user: dict = Depends(get_current_user)):
    db.connections.update_one(
        {"user": current_user["username"], "provider": provider},
        {"$set": {"status": "connected", "updated_at": datetime.now(UTC)}},
        upsert=True)
    db.events.insert_one({
        "user": current_user["username"],
        "type": "connection",
        "source": provider,
        "date": datetime.now(UTC),
        "summary": f"Connected {provider}",
        "tags": [provider]
    })
    return HTMLResponse(f"<p>{provider} connected. <a href='/dashboard'>Back</a></p>")
