from datetime import datetime, timezone
import csv
import io

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import get_current_user
from app.db import db

router = APIRouter(prefix="/org/oil", tags=["org_oil"])

templates = Jinja2Templates(directory="app/templates")

oil_incidents = db["oil_gas_incidents"]
oil_permits = db["oil_gas_permits"]
oil_trainings = db["oil_gas_trainings"]

# --- Pages

@router.get("/incidents/new", response_class=HTMLResponse)
def new_incident_page(request: Request, user=Depends(get_current_user)):
    """ Simple intake form page for a new incident"""
    return templates.TemplateResponse(
        "oil_new_incident.html",
        {"request": request, "user": user},
    )

@router.post("/incidents/new", response_class=HTMLResponse)
async def create_incident(request: Request, user=Depends(get_current_user)):
    """Handle incident intake form submit"""
    form = await request.form()
    
    doc = {
        "org_id": user.get("org_id"),
        "demo": True,  # keep it marked as demo for now
        "ts": datetime.now(timezone.utc).isoformat(),
        "site": form.get("site") or "Unknown",
        "type": form.get("type") or "incident",
        "severity": form.get("severity") or "low",
        "status": form.get("status") or "open",
        "description": form.get("description") or "",
        "created_by": user.get("username"),
    }
    oil_incidents.insert_one(doc)

    # send them back to main dashboard
    return RedirectResponse("/dashboard", status_code=303)



# ------ Actions / APIs

@router.post("/audit")
def run_safety_audit(user=Depends(get_current_user)):
    """
    For now this just acknowledges a 'queued' audit.
    Later yhou can add logic to recompute risk, create an audit record, etc.
    """
    #example placeholder: count high severity open incidents
    high_open = oil_incidents.count_documents({
        "org_id": user.get("org_id"),
        "severity": "high",
        "status": {"$in": ["open", "investigating"]},
    })
    return {
        "status": "ok",
        "message": f"Safety audit queued. {high_open} open high-severity incidents.",
    }

@router.get("/report")
def export_compliance_report(user=Depends(get_current_user)):
    """Stream a CSV of all incidents for this org."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["when", "site", "type", "severity", "status"])

    for inc in oil_incidents.find({"org_id": user.get("org_id")}):
        writer.writerow([
            inc.get("ts"),
            inc.get("site"),
            inc.get("type"),
            inc.get("severity"),
            inc.get("status"),
        ])

        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=oil_compliance.csv"},
    )