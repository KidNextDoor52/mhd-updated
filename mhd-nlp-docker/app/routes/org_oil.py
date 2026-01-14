# app/routes/org_oil.py
from datetime import datetime, timezone
import csv
import io

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import get_current_user
from app.audit import write_audit_event
from app.db import db
from app.authz import require_org_user, require_vertical

router = APIRouter(prefix="/org/oil", tags=["org_oil"])
templates = Jinja2Templates(directory="app/templates")

oil_incidents = db["oil_gas_incidents"]
oil_permits = db["oil_gas_permits"]
oil_trainings = db["oil_gas_trainings"]


# --- Pages

@router.get(
    "/incidents/new",
    response_class=HTMLResponse,
    dependencies=[Depends(require_org_user), Depends(require_vertical("oil_gas"))],
)
def new_incident_page(request: Request, user=Depends(get_current_user)):
    """Simple intake form page for a new incident"""
    return templates.TemplateResponse(
        "oil_new_incident.html",
        {"request": request, "user": user},
    )


@router.post(
    "/incidents/new",
    response_class=HTMLResponse,
    dependencies=[Depends(require_org_user), Depends(require_vertical("oil_gas"))],
)
async def create_incident(request: Request, user=Depends(get_current_user)):
    """Handle incident intake form submit"""
    form = await request.form()
    org_id = user.get("org_id")

    doc = {
        "org_id": org_id,
        "demo": True,
        "ts": datetime.now(timezone.utc).isoformat(),
        "site": form.get("site") or "Unknown",
        "type": form.get("type") or "incident",
        "severity": form.get("severity") or "low",
        "status": form.get("status") or "open",
        "description": form.get("description") or "",
        "created_by": user.get("username"),
    }
    oil_incidents.insert_one(doc)

    write_audit_event(
        tenant_id=org_id,
        user_id=user.get("username") or user.get("_id"),
        action="oil_incident_created",
        resource_type="oil_gas_incident",
        resource_id=str(doc.get("site")),
        extra={"severity": doc["severity"], "status": doc["status"]},
        request=request,
    )

    return RedirectResponse("/dashboard", status_code=303)


# ------ Actions / APIs

@router.post(
    "/audit",
    dependencies=[Depends(require_org_user), Depends(require_vertical("oil_gas"))],
)
def run_safety_audit(request: Request, user=Depends(get_current_user)):
    """
    Placeholder "audit": count high severity open incidents.
    """
    org_id = user.get("org_id")

    high_open = oil_incidents.count_documents({
        "org_id": org_id,
        "severity": "high",
        "status": {"$in": ["open", "investigating"]},
    })

    write_audit_event(
        tenant_id=org_id,
        user_id=user.get("username") or user.get("_id"),
        action="oil_safety_audit_requested",
        resource_type="oil_gas_incidents",
        extra={"high_open": high_open},
        request=request,
    )

    return {
        "status": "ok",
        "message": f"Safety audit queued. {high_open} open high-severity incidents.",
    }


@router.get(
    "/report",
    dependencies=[Depends(require_org_user), Depends(require_vertical("oil_gas"))],
)
def export_compliance_report(request: Request, user=Depends(get_current_user)):
    """Stream a CSV of all incidents for this org."""
    org_id = user.get("org_id")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["when", "site", "type", "severity", "status"])

    for inc in oil_incidents.find({"org_id": org_id}):
        writer.writerow([
            inc.get("ts"),
            inc.get("site"),
            inc.get("type"),
            inc.get("severity"),
            inc.get("status"),
        ])

    buf.seek(0)

    write_audit_event(
        tenant_id=org_id,
        user_id=user.get("username") or user.get("_id"),
        action="oil_compliance_report_exported",
        resource_type="oil_gas_incidents",
        extra={"format": "csv"},
        request=request,
    )

    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=oil_compliance.csv"},
    )
