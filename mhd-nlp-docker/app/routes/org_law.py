# app/routes/org_law.py
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

router = APIRouter(prefix="/org/law", tags=["org_law"])
templates = Jinja2Templates(directory="app/templates")

law_matters = db["law_matters"]
law_deadlines = db["law_deadlines"]
law_signatures = db["law_signatures"]


# ---------- Pages ----------

@router.get(
    "/matters/new",
    response_class=HTMLResponse,
    dependencies=[Depends(require_org_user), Depends(require_vertical("law"))],
)
def new_matter_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "law_new_matter.html",
        {"request": request, "user": user},
    )


@router.post(
    "/matters/new",
    response_class=HTMLResponse,
    dependencies=[Depends(require_org_user), Depends(require_vertical("law"))],
)
async def create_matter(request: Request, user=Depends(get_current_user)):
    form = await request.form()
    org_id = user.get("org_id")

    doc = {
        "org_id": org_id,
        "demo": True,
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "name": form.get("name") or "New Matter",
        "client": form.get("client") or "Client",
        "owner": form.get("owner") or user.get("username"),
        "status": form.get("status") or "open",
        "created_by": user.get("username"),
    }
    law_matters.insert_one(doc)

    write_audit_event(
        tenant_id=org_id,
        user_id=user.get("username") or user.get("_id"),
        action="law_matter_created",
        resource_type="law_matter",
        resource_id=str(doc.get("name")),
        extra={"status": doc["status"], "client": doc["client"]},
        request=request,
    )

    return RedirectResponse("/dashboard", status_code=303)


# ---------- Actions / APIs ----------

@router.get(
    "/deadlines/upcoming",
    dependencies=[Depends(require_org_user), Depends(require_vertical("law"))],
)
def get_upcoming_deadlines(request: Request, user=Depends(get_current_user)):
    """
    Simple JSON API for upcoming deadlines (org-scoped).
    """
    org_id = user.get("org_id")

    items = []
    for d in law_deadlines.find({"org_id": org_id}):
        items.append({
            "name": d.get("name"),
            "matter_name": d.get("matter_name"),
            "owner": d.get("owner"),
            "due_at": d.get("due_at"),
        })

    write_audit_event(
        tenant_id=org_id,
        user_id=user.get("username") or user.get("_id"),
        action="law_deadlines_viewed",
        resource_type="law_deadlines",
        extra={"count": len(items)},
        request=request,
    )

    return {"items": items}


@router.get(
    "/docket",
    dependencies=[Depends(require_org_user), Depends(require_vertical("law"))],
)
def export_docket(request: Request, user=Depends(get_current_user)):
    """Export a simple docket CSV of matters."""
    org_id = user.get("org_id")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["matter", "client", "owner", "status", "opened_at"])

    for m in law_matters.find({"org_id": org_id}):
        writer.writerow([
            m.get("name"),
            m.get("client"),
            m.get("owner"),
            m.get("status"),
            m.get("opened_at"),
        ])

    buf.seek(0)

    write_audit_event(
        tenant_id=org_id,
        user_id=user.get("username") or user.get("_id"),
        action="law_docket_exported",
        resource_type="law_matters",
        extra={"format": "csv"},
        request=request,
    )

    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=docket.csv"},
    )
