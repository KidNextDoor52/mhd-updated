# app/routes/org_law.py
from datetime import datetime, timezone
import csv
import io

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import get_current_user
from app.db import db

router = APIRouter(prefix="/org/law", tags=["org_law"])

templates = Jinja2Templates(directory="app/templates")

law_matters = db["law_matters"]
law_deadlines = db["law_deadlines"]
law_signatures = db["law_signatures"]


# ---------- Pages ----------

@router.get("/matters/new", response_class=HTMLResponse)
def new_matter_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "law_new_matter.html",
        {"request": request, "user": user},
    )


@router.post("/matters/new", response_class=HTMLResponse)
async def create_matter(request: Request, user=Depends(get_current_user)):
    form = await request.form()

    doc = {
        "org_id": user.get("org_id"),
        "demo": True,
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "name": form.get("name") or "New Matter",
        "client": form.get("client") or "Client",
        "owner": form.get("owner") or user.get("username"),
        "status": form.get("status") or "open",
    }
    law_matters.insert_one(doc)
    return RedirectResponse("/dashboard", status_code=303)


# ---------- Actions / APIs ----------

@router.get("/deadlines/upcoming")
def get_upcoming_deadlines(user=Depends(get_current_user)):
    """
    Example JSON API you could later hit from a 'Deadlines' page.
    For now, not strictly required for the button which just scrolls.
    """
    now = datetime.now(timezone.utc)
    items = []
    for d in law_deadlines.find({"org_id": user.get("org_id")}):
        items.append({
            "name": d.get("name"),
            "matter_name": d.get("matter_name"),
            "owner": d.get("owner"),
            "due_at": d.get("due_at"),
        })
    return {"items": items}


@router.get("/docket")
def export_docket(user=Depends(get_current_user)):
    """Export a simple docket CSV of open matters + key deadlines."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["matter", "client", "owner", "status", "opened_at"])

    for m in law_matters.find({"org_id": user.get("org_id")}):
        writer.writerow([
            m.get("name"),
            m.get("client"),
            m.get("owner"),
            m.get("status"),
            m.get("opened_at"),
        ])

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=docket.csv"},
    )
