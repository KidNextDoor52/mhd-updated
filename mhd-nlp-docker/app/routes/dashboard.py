from datetime import datetime, timezone
import pandas as pd

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import get_current_user
from app.authz import require_role
from app.db import db

from collections import defaultdict

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")

# ---- Core MHD collections ----
uploads_col = db.uploads
medical_history_col = db.medical_history
equipment_col = db.equipment
training_col = db.training
weightroom_col = db.weightroom
activity_logs_col = db.activity_logs

risk = db["risk_predictions"]
metrics_coll = db["model_daily_metrics"]

# ---- Industry collections ----
oil_incidents = db["oil_gas_incidents"]
oil_permits = db["oil_gas_permits"]
oil_trainings = db["oil_gas_trainings"]

fin_clients = db["financial_clients"]
fin_alerts = db["financial_alerts"]
fin_kyc = db["financial_kyc"]

law_matters = db["law_matters"]
law_deadlines = db["law_deadlines"]
law_signatures = db["law_signatures"]


# ================= TRAINER JSON / LEGACY VIEW =====================

@router.get(
    "/trainer",
    response_class=HTMLResponse,
    dependencies=[Depends(require_role("trainer"))],
)
async def trainer_dashboard_legacy(request: Request, user=Depends(get_current_user)):
    """
    Legacy trainer route: kept for backwards compatibility.
    New trainer view lives at /trainer/dashboard via app/routes/trainer_dashboard.py.
    """
    return templates.TemplateResponse(
        "trainer_dashboard.html",
        {
            "request": request,
            "user": user,
        },
    )


@router.get(
    "/trainer/top_risk",
    dependencies=[Depends(require_role("trainer"))],
)
async def top_risk(limit: int = 20):
    rows = list(risk.find().sort("ts", -1).limit(2000))
    if not rows:
        return []

    df = pd.DataFrame(rows)
    latest = df.sort_values(["athlete_id", "ts"]).groupby("athlete_id").tail(1)
    top = latest.sort_values("score", ascending=False).head(limit)

    return [
        {
            "athlete_id": str(r["athlete_id"]),
            "risk": float(r["score"]),
            "run_id": r.get("run_id"),
            "model_version": r.get("model_version"),
        }
        for _, r in top.iterrows()
    ]


@router.get(
    "/trainer/metrics",
    dependencies=[Depends(require_role("trainer"))],
)
async def trainer_metrics():
    rows = list(metrics_coll.find().sort("day", -1).limit(14))
    return [
        {
            "day": r["day"],
            "precision_at_k": r.get("precision_at_k"),
            "n": r.get("n"),
            "k_pct": r.get("k_pct"),
        }
        for r in rows
    ]


# ================= SHARED ATHLETE HELPERS =========================

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
    if not value:
        return "—"
    return value.replace("_", " ").title()


# ================= MAIN /dashboard DISPATCHER =====================

@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Entry point for all dashboards.

    Dispatch rules:
      - trainer/admin -> redirect to /trainer/dashboard
      - vertical == oil_gas   -> dashboard_oil_gas.html
      - vertical == financial -> dashboard_financial.html
      - vertical == law       -> dashboard_law.html
      - otherwise             -> athlete / health_sports dashboard.html
    """
    username = current_user["username"]
    role = current_user.get("role")
    vertical = current_user.get("vertical")
    org_id = current_user.get("org_id")

    # 1) Trainer/admin → dedicated trainer command center
    if role in ("trainer", "admin"):
        return RedirectResponse("/trainer/dashboard", status_code=307)

    # 2) Oil & Gas org view
    if vertical == "oil_gas":
        return _render_oil_gas_dashboard(request, current_user, org_id)

    # 3) Financial org view
    if vertical == "financial":
        return _render_financial_dashboard(request, current_user, org_id)

    # 4) Law org view
    if vertical == "law":
        return _render_law_dashboard(request, current_user, org_id)

    # 5) Default: athlete / health_sports view (existing logic)
    docs = list(
        uploads_col.find({"username": username})
        .sort("upload_date", -1)
        .limit(10)
    )
    doc_count = uploads_col.count_documents({"username": username})

    grouped_docs = {"medical": [], "performance": [], "equipment": []}
    for d in docs:
        for cat in (d.get("category") or []):
            k = (cat or "").strip().lower()
            if k in grouped_docs:
                grouped_docs[k].append(d)

    medical = medical_history_col.find_one({"username": username}) or {}

    user_equipment = equipment_col.find_one({"username": username}) or {}
    if not isinstance(user_equipment.get("items"), list):
        user_equipment["items"] = []
    for it in user_equipment["items"]:
        for key in ["category", "brand", "type", "size", "notes"]:
            if key in it:
                it[key] = format_label(it[key])

    training_logs = list(
        training_col.find({"username": username}).sort("_id", -1).limit(5)
    )
    training_count = training_col.count_documents({"username": username})

    weightroom_stats = weightroom_col.find_one({"username": username}) or {}

    activity = list(
        activity_logs_col.find({"user_id": username})
        .sort("_id", -1)
        .limit(5)
    )
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


# ================= OIL & GAS DASHBOARD RENDERER ===================

def _render_oil_gas_dashboard(request: Request, user: dict, org_id: str | None):
    org_filter = {"org_id": org_id} if org_id else {}

    inc_docs = list(
        oil_incidents.find({"demo": True, **org_filter}).sort("ts", -1).limit(50)
    )
    incidents_total = len(inc_docs)
    incidents_high = sum(1 for d in inc_docs if d.get("severity") == "high")
    incidents_open = sum(
        1 for d in inc_docs if d.get("status") in ("open", "investigating")
    )

    now = datetime.now(timezone.utc)
    permits_docs = list(
        oil_permits.find({"demo": True, **org_filter}).limit(50)
    )
    permits_30d = 0
    permits_60d = 0
    permits_upcoming = []
    for p in permits_docs:
        exp_str = p.get("expires_at")
        try:
            exp = datetime.fromisoformat(exp_str).replace(tzinfo=timezone.utc)
        except Exception:
            continue
        days = (exp - now).days
        if 0 <= days <= 30:
            permits_30d += 1
        if 0 <= days <= 60:
            permits_60d += 1
        if days >= 0:
            permits_upcoming.append(p)

    trainings_docs = list(
        oil_trainings.find({"demo": True, **org_filter}).limit(100)
    )
    trainings_on_time = sum(1 for t in trainings_docs if t.get("status") == "on_time")
    trainings_overdue = sum(1 for t in trainings_docs if t.get("status") == "overdue")

    # Simple placeholder “trend” (replace with real logic later)
    risk_direction = "Stable"
    risk_delta = 0.0

    return templates.TemplateResponse(
        "dashboard_oil_gas.html",
        {
            "request": request,
            "user": user,
            "incidents_total": incidents_total,
            "incidents_high": incidents_high,
            "incidents_open": incidents_open,
            "permits_30d": permits_30d,
            "permits_60d": permits_60d,
            "trainings_on_time": trainings_on_time,
            "trainings_overdue": trainings_overdue,
            "risk_direction": risk_direction,
            "risk_delta": risk_delta,
            "recent_incidents": inc_docs[:10],
            "permits_upcoming": permits_upcoming[:10],
            "training_status": trainings_docs[:20],
        },
    )


# ================= FINANCIAL DASHBOARD RENDERER ===================

def _render_financial_dashboard(request: Request, user: dict, org_id: str | None):
    org_filter = {"org_id": org_id} if org_id else {}

    clients = list(fin_clients.find({"demo": True, **org_filter}).limit(200))
    clients_active = sum(1 for c in clients if c.get("status") == "active")
    clients_onboarding = sum(1 for c in clients if c.get("status") == "onboarding")

    alerts = list(
        fin_alerts.find({"demo": True, **org_filter}).sort("ts", -1).limit(100)
    )
    accounts_high_risk = len(alerts)
    accounts_under_review = sum(1 for a in alerts if a.get("status") == "review")

    # ---- build simple alerts-by-day series for sparkline ----
    alerts_by_day_map: dict[str, int] = defaultdict(int)
    for a in alerts:
        ts = a.get("ts")
        if isinstance(ts, datetime):
            day_str = ts.date().isoformat()
        else:
            # assume ISO string
            day_str = str(ts)[:10]
        alerts_by_day_map[day_str] += 1

    # sort by day ascending
    alerts_by_day = [
        {"day": day, "count": alerts_by_day_map[day]}
        for day in sorted(alerts_by_day_map.keys())
    ]

    kyc_docs = list(fin_kyc.find({"demo": True, **org_filter}).limit(100))
    kyc_pending = sum(1 for k in kyc_docs if k.get("status") == "pending")
    kyc_overdue = sum(1 for k in kyc_docs if k.get("status") == "overdue")

    alerts_direction = "Stable"
    alerts_delta = 0.0

    high_risk_accounts = alerts
    kyc_queue = kyc_docs
    recent_activity = []  # later: map from audit logs

    return templates.TemplateResponse(
        "dashboard_financial.html",
        {
            "request": request,
            "user": user,
            "clients_active": clients_active,
            "clients_onboarding": clients_onboarding,
            "kyc_pending": kyc_pending,
            "kyc_overdue": kyc_overdue,
            "accounts_high_risk": accounts_high_risk,
            "accounts_under_review": accounts_under_review,
            "alerts_direction": alerts_direction,
            "alerts_delta": alerts_delta,
            "high_risk_accounts": high_risk_accounts,
            "kyc_queue": kyc_queue,
            "recent_activity": recent_activity,
            # chart series
            "alerts_by_day": alerts_by_day,
        },
    )



# ================= LAW / LEGAL DASHBOARD RENDERER =================

def _render_law_dashboard(request: Request, user: dict, org_id: str | None):
    org_filter = {"org_id": org_id} if org_id else {}

    matters = list(
        law_matters.find({"demo": True, **org_filter}).limit(200)
    )
    matters_open = sum(1 for m in matters if m.get("status") == "open")

    now = datetime.now(timezone.utc)
    matters_new_month = 0
    for m in matters:
        opened = m.get("opened_at")
        try:
            opened_dt = datetime.fromisoformat(opened).replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if (now - opened_dt).days <= 30:
            matters_new_month += 1

    deadlines = list(
        law_deadlines.find({"demo": True, **org_filter}).limit(200)
    )
    deadlines_7d = 0
    deadlines_14d = 0
    upcoming_deadlines = []
    for d in deadlines:
        due_str = d.get("due_at")
        try:
            due = datetime.fromisoformat(due_str).replace(tzinfo=timezone.utc)
        except Exception:
            continue
        days = (due - now).days
        if 0 <= days <= 7:
            deadlines_7d += 1
        if 0 <= days <= 14:
            deadlines_14d += 1
        if days >= 0:
            upcoming_deadlines.append(d)

    sigs = list(
        law_signatures.find({"demo": True, **org_filter}).limit(200)
    )
    signatures_pending = sum(1 for s in sigs if s.get("status") == "pending")
    signatures_overdue = sum(1 for s in sigs if s.get("status") == "overdue")

    workload_direction = "Stable"
    workload_delta = 0.0

    return templates.TemplateResponse(
        "dashboard_law.html",
        {
            "request": request,
            "user": user,
            "matters_open": matters_open,
            "matters_new_month": matters_new_month,
            "deadlines_7d": deadlines_7d,
            "deadlines_14d": deadlines_14d,
            "signatures_pending": signatures_pending,
            "signatures_overdue": signatures_overdue,
            "workload_direction": workload_direction,
            "workload_delta": workload_delta,
            "open_matters": matters,
            "upcoming_deadlines": upcoming_deadlines,
            "signature_queue": sigs,
        },
    )
