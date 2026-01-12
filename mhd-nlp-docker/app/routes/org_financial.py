# app/routes/org_financial.py
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

router = APIRouter(prefix="/org/fin", tags=["org_financial"])
templates = Jinja2Templates(directory="app/templates")

fin_clients = db["financial_clients"]
fin_alerts = db["financial_alerts"]
fin_kyc = db["financial_kyc"]


# ---------- Pages ----------

@router.get(
    "/clients/new",
    response_class=HTMLResponse,
    dependencies=[Depends(require_org_user), Depends(require_vertical("financial"))],
)
def new_client_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "fin_new_client.html",
        {"request": request, "user": user},
    )


@router.post(
    "/clients/new",
    response_class=HTMLResponse,
    dependencies=[Depends(require_org_user), Depends(require_vertical("financial"))],
)
async def create_client(request: Request, user=Depends(get_current_user)):
    form = await request.form()
    org_id = user.get("org_id")

    doc = {
        "org_id": org_id,
        "demo": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "client_name": form.get("client_name") or "New Client",
        "status": form.get("status") or "onboarding",
        "segment": form.get("segment") or "retail",
        "created_by": user.get("username"),
    }
    fin_clients.insert_one(doc)

    write_audit_event(
        tenant_id=org_id,
        user_id=user.get("username") or user.get("_id"),
        action="fin_client_created",
        resource_type="financial_client",
        resource_id=str(doc.get("client_name")),
        extra={"status": doc["status"], "segment": doc["segment"]},
        request=request,
    )

    return RedirectResponse("/dashboard", status_code=303)


# ---------- Actions / APIs ----------

@router.post(
    "/kyc/batch",
    dependencies=[Depends(require_org_user), Depends(require_vertical("financial"))],
)
def run_kyc_batch(request: Request, user=Depends(get_current_user)):
    """
    Placeholder: mark all 'pending' KYC items for this org as 'in_progress'.
    """
    org_id = user.get("org_id")
    result = fin_kyc.update_many(
        {"org_id": org_id, "status": "pending"},
        {"$set": {"status": "in_progress", "updated_at": datetime.now(timezone.utc).isoformat()}},
    )

    write_audit_event(
        tenant_id=org_id,
        user_id=user.get("username") or user.get("_id"),
        action="fin_kyc_batch_started",
        resource_type="financial_kyc",
        extra={"modified_count": result.modified_count},
        request=request,
    )

    return {
        "status": "ok",
        "message": f"KYC batch started for {result.modified_count} records.",
    }


@router.get(
    "/report",
    dependencies=[Depends(require_org_user), Depends(require_vertical("financial"))],
)
def export_risk_report(request: Request, user=Depends(get_current_user)):
    """Export current high-risk accounts as CSV."""
    org_id = user.get("org_id")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["account_id", "client_name", "score", "status"])

    for a in fin_alerts.find({"org_id": org_id}):
        writer.writerow([
            a.get("account_id"),
            a.get("client_name"),
            a.get("score"),
            a.get("status"),
        ])

    buf.seek(0)

    write_audit_event(
        tenant_id=org_id,
        user_id=user.get("username") or user.get("_id"),
        action="fin_risk_report_exported",
        resource_type="financial_alerts",
        extra={"format": "csv"},
        request=request,
    )

    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=financial_risk.csv"},
    )
