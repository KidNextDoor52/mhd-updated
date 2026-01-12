# app/routes/org_financial.py
from datetime import datetime, timezone
import csv
import io

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import get_current_user
from app.db import db

router = APIRouter(prefix="/org/fin", tags=["org_financial"])

templates = Jinja2Templates(directory="app/templates")

fin_clients = db["financial_clients"]
fin_alerts = db["financial_alerts"]
fin_kyc = db["financial_kyc"]


# ---------- Pages ----------

@router.get("/clients/new", response_class=HTMLResponse)
def new_client_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "fin_new_client.html",
        {"request": request, "user": user},
    )


@router.post("/clients/new", response_class=HTMLResponse)
async def create_client(request: Request, user=Depends(get_current_user)):
    form = await request.form()

    doc = {
        "org_id": user.get("org_id"),
        "demo": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "client_name": form.get("client_name") or "New Client",
        "status": form.get("status") or "onboarding",
        "segment": form.get("segment") or "retail",
    }
    fin_clients.insert_one(doc)
    return RedirectResponse("/dashboard", status_code=303)


# ---------- Actions / APIs ----------

@router.post("/kyc/batch")
def run_kyc_batch(user=Depends(get_current_user)):
    """
    Placeholder: mark all 'pending' KYC items for this org as 'in_progress'.
    """
    org_id = user.get("org_id")
    result = fin_kyc.update_many(
      {"org_id": org_id, "status": "pending"},
      {"$set": {"status": "in_progress"}}
    )
    return {
        "status": "ok",
        "message": f"KYC batch started for {result.modified_count} records.",
    }


@router.get("/report")
def export_risk_report(user=Depends(get_current_user)):
    """Export current high-risk accounts as CSV."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["account_id", "client_name", "score", "status"])

    for a in fin_alerts.find({"org_id": user.get("org_id")}):
        writer.writerow([
            a.get("account_id"),
            a.get("client_name"),
            a.get("score"),
            a.get("status"),
        ])

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=financial_risk.csv"},
    )
