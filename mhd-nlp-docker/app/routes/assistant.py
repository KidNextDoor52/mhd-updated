# app/routes/assistant.py
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import json

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.auth import get_current_user
from app.db import db

router = APIRouter(prefix="/assistant", tags=["assistant"])

UTC = timezone.utc

# --------- collections (aligned with your seed scripts) ---------

# financial
fin_clients         = db["financial_clients"]
fin_kyc_queue       = db["financial_kyc"]
fin_high_risk_accts = db["financial_alerts"]     # high-risk accounts / alerts
fin_alert_events    = db["financial_alerts"]

# law
law_matters         = db["law_matters"]
law_deadlines       = db["law_deadlines"]
law_signatures      = db["law_signatures"]

# oil & gas
oil_incidents       = db["oil_gas_incidents"]
oil_permits         = db["oil_gas_permits"]
oil_training        = db["oil_gas_trainings"]

# trainer / athletes
trainer_preds       = db["predictions"]  # injury_risk + session_quality
trainer_sessions    = db["sessions"]     # raw sessions (no scores, used later if you want)


class AssistantQuery(BaseModel):
    message: str


# --------- small helpers ---------


def _clean(s: str) -> str:
    return (s or "").lower().strip()


def _days_ago(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


# --------- FINANCIAL intents ---------


def answer_financial(msg: str, user: Dict[str, Any]) -> str:
    org_id = user.get("org_id")
    m = _clean(msg)

    # 1) high-risk accounts
    if "high risk" in m and ("how many" in m or "count" in m or "number" in m):
        n = fin_high_risk_accts.count_documents({"org_id": org_id})
        return f"You currently have {n} high-risk account{'s' if n != 1 else ''} in monitoring."

    # 2) what's overdue? (KYC)
    if "overdue" in m or "late" in m:
        n = fin_kyc_queue.count_documents({"org_id": org_id, "status": "overdue"})
        if n == 0:
            return "There are no overdue KYC / AML checks right now."
        top = list(
            fin_kyc_queue.find(
                {"org_id": org_id, "status": "overdue"},
                {"client_name": 1, "due_at": 1},
            )
            .sort("due_at", 1)
            .limit(3)
        )
        names = ", ".join(t.get("client_name", "Unknown") for t in top)
        return f"You have {n} overdue KYC / AML check(s). Oldest items include: {names}."

    # 3) what looks most at risk
    if "what looks most at risk" in m or "where should i focus" in m:
        high_n = fin_high_risk_accts.count_documents({"org_id": org_id})
        overdue_n = fin_kyc_queue.count_documents({"org_id": org_id, "status": "overdue"})
        return (
            "Right now the main risk drivers are:\n"
            f"• {high_n} high-risk account(s)\n"
            f"• {overdue_n} overdue KYC / AML check(s)\n"
            "Start with the overdue checks on your highest-risk clients."
        )

    # 4) KYC queue snapshot
    if "kyc" in m and ("queue" in m or "pending" in m):
        pending = fin_kyc_queue.count_documents({"org_id": org_id, "status": "pending"})
        overdue = fin_kyc_queue.count_documents({"org_id": org_id, "status": "overdue"})
        return (
            f"There are {pending} KYC / AML checks pending and "
            f"{overdue} overdue for your org."
        )

    # default
    return (
        "I can help interpret your financial dashboards. Try asking things like:\n"
        "• \"How many accounts are high-risk?\"\n"
        "• \"What’s overdue in the KYC queue?\"\n"
        "• \"What looks most at risk right now?\""
    )


# --------- LAW intents ---------


def answer_law(msg: str, user: Dict[str, Any]) -> str:
    org_id = user.get("org_id")
    m = _clean(msg)

    # open matters
    if "open matter" in m or "open matters" in m:
        n = law_matters.count_documents({"org_id": org_id, "status": "open"})
        return f"You currently have {n} open matter{'s' if n != 1 else ''}."

    # upcoming deadlines (simple but robust date handling)
    if "deadline" in m or "due" in m:
        now = datetime.now(UTC).date()
        in_7 = now + timedelta(days=7)
        in_14 = now + timedelta(days=14)

        upcoming = list(law_deadlines.find({"org_id": org_id}))
        n7 = 0
        n14 = 0
        for d in upcoming:
            raw = d.get("due_at")
            if not raw:
                continue
            try:
                due_date = (
                    raw.date()
                    if isinstance(raw, datetime)
                    else datetime.fromisoformat(str(raw)).date()
                )
            except Exception:
                continue
            if now <= due_date <= in_7:
                n7 += 1
            elif in_7 < due_date <= in_14:
                n14 += 1

        return (
            f"In the next 7 days you have {n7} deadline(s), "
            f"and {n14} additional deadline(s) in the following week."
        )

    # docs awaiting signature
    if "signature" in m or "signatures" in m or "docs" in m:
        pending = law_signatures.count_documents({"org_id": org_id, "status": "pending"})
        overdue = law_signatures.count_documents({"org_id": org_id, "status": "overdue"})
        return (
            f"There are {pending} document(s) pending signature and "
            f"{overdue} overdue for your firm."
        )

    return (
        "I can help you understand your legal ops workload. Try questions like:\n"
        "• \"How many open matters do we have?\"\n"
        "• \"What deadlines are coming up?\"\n"
        "• \"How many docs are waiting on signature?\""
    )


# --------- OIL & GAS intents ---------


def answer_oil(msg: str, user: Dict[str, Any]) -> str:
    org_id = user.get("org_id")
    m = _clean(msg)

    # incidents this month / high-severity / open
    if "incident" in m:
        since = _days_ago(30)
        total = oil_incidents.count_documents({"org_id": org_id, "ts": {"$gte": since}})
        high = oil_incidents.count_documents(
            {"org_id": org_id, "ts": {"$gte": since}, "severity": "high"}
        )
        open_n = oil_incidents.count_documents(
            {"org_id": org_id, "status": {"$ne": "closed"}}
        )
        return (
            f"In the last 30 days you have {total} incident(s), "
            f"{high} of them high-severity, with {open_n} still open."
        )

    # permits expiring
    if "permit" in m or "certification" in m:
        now = datetime.now(UTC).date()
        in_30 = now + timedelta(days=30)
        in_60 = now + timedelta(days=60)

        permits = list(oil_permits.find({"org_id": org_id}))
        n30 = 0
        n60 = 0
        for p in permits:
            raw = p.get("expires_at")
            if not raw:
                continue
            try:
                exp = (
                    raw.date()
                    if isinstance(raw, datetime)
                    else datetime.fromisoformat(str(raw)).date()
                )
            except Exception:
                continue
            if now <= exp <= in_30:
                n30 += 1
            elif in_30 < exp <= in_60:
                n60 += 1

        return (
            f"You have {n30} permit(s) expiring in the next 30 days and "
            f"{n60} more in days 31–60."
        )

    # safety training
    if "training" in m or "safety" in m or "compliance" in m:
        on_time = oil_training.count_documents({"org_id": org_id, "status": "on_time"})
        overdue = oil_training.count_documents({"org_id": org_id, "status": "overdue"})
        return (
            f"Training compliance snapshot: {on_time} employee(s) on-time, "
            f"{overdue} overdue."
        )

    return (
        "I can summarize safety and compliance. Try asking:\n"
        "• \"How many incidents this month?\"\n"
        "• \"Any permits expiring soon?\"\n"
        "• \"How many employees are overdue on safety training?\""
    )


# --------- TRAINER intents (UI-context first, DB fallback) ---------


def answer_trainer(
    msg: str,
    user: Dict[str, Any],
    ui_ctx: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Trainer assistant.

    1) If ui_ctx is provided (from X-MHD-Context), use that so answers
       always match what the trainer sees on the dashboard.
    2) If no context is present, fall back to DB queries over `predictions`.
    """
    # org_id kept for future; demo data doesn't use it today
    org_id = user.get("org_id")
    m = _clean(msg)
    ui_ctx = ui_ctx or {}

    # ---- 1. UI-context driven answers ----
    if ui_ctx:
        risk_dist = ui_ctx.get("risk_distribution") or {}
        needs_clearance = ui_ctx.get("needs_clearance") or []
        live_high = ui_ctx.get("live_high_risk") or []
        top_at = ui_ctx.get("top_at_risk") or []
        session_quality = ui_ctx.get("session_quality") or {}

        # counts
        if "how many" in m and "high" in m and "risk" in m:
            return f"There are {risk_dist.get('high', 0)} high-risk athletes right now."

        if "how many" in m and "medium" in m and "risk" in m:
            return f"There are {risk_dist.get('medium', 0)} medium-risk athletes."

        if "how many" in m and "low" in m and "risk" in m:
            return f"There are {risk_dist.get('low', 0)} low-risk athletes."

        # who's high risk
        if "who" in m and "high" in m and "risk" in m:
            names = [a.get("athlete_id") for a in live_high] or [
                a.get("athlete_id") for a in top_at
            ]
            if not names:
                return "No athletes are currently marked high-risk."
            return "High-risk athletes: " + ", ".join(names[:10])

        # who needs clearance
        if "who" in m and ("need clearance" in m or "needs clearance" in m):
            names = [a.get("athlete_id") for a in needs_clearance]
            if not names:
                return "No athletes currently need clearance."
            return "These athletes need clearance: " + ", ".join(names[:10])

        # session quality (uses UI metrics)
        if "average" in m and "session" in m:
            avg = session_quality.get("avg_quality")
            sc = session_quality.get("sessions_scored", 0)
            if avg is None:
                return "I don’t see any recent session quality scores yet."
            return (
                f"Over the last 7 days, {sc} sessions were scored "
                f"with an average quality of {avg:.1f}/5."
            )

        # at-risk list
        if "at risk" in m or "top risk" in m:
            if not top_at:
                return "No at-risk athletes detected right now."
            formatted = [
                f"{a.get('athlete_id')} (score {a.get('risk_score')})"
                for a in top_at[:5]
            ]
            return "Top at-risk athletes: " + ", ".join(formatted)

        # generic trainer fallback when context exists
        return (
            "I can help you see who’s most at risk and how sessions look. Try:\n"
            "• \"Who is high-risk right now?\"\n"
            "• \"How many athletes are low risk?\"\n"
            "• \"Which athletes need clearance?\"\n"
            "• \"What’s the average session score in the last 7 days?\""
        )

    # ---- 2. DB fallback (no UI context header) ----
    # Here we read directly from `predictions`, which matches your seed_demo_data.

    # High-risk: use injury_risk predictions with score thresholds
    if "high risk" in m or "who is high-risk" in m or "who is high risk" in m:
        since = _days_ago(7)
        high = list(
            trainer_preds.find(
                {
                    "use_case": "injury_risk",
                    "ts": {"$gte": since},
                    "score": {"$gte": 0.75},
                },
                {"athlete_id": 1, "score": 1},
            )
            .sort("score", -1)
            .limit(5)
        )
        if not high:
            return "There are no athletes currently in the high-risk band."
        names = ", ".join(
            f"{p.get('athlete_id','unknown')} ({p.get('score'):.2f})"
            for p in high
        )
        return f"High-risk athletes right now include: {names}."

    if "medium risk" in m or "who is medium" in m:
        since = _days_ago(7)
        med = trainer_preds.count_documents(
            {
                "use_case": "injury_risk",
                "ts": {"$gte": since},
                "score": {"$gte": 0.4, "$lt": 0.75},
            }
        )
        return f"There are {med} athlete(s) in the medium risk band."

    if "low risk" in m:
        since = _days_ago(7)
        low = trainer_preds.count_documents(
            {
                "use_case": "injury_risk",
                "ts": {"$gte": since},
                "score": {"$lt": 0.4},
            }
        )
        return f"There are {low} athlete(s) in the low risk band."

    # average session score -> use session_quality predictions, not sessions
    if "average" in m and "session" in m:
        since = _days_ago(7)
        q = {
            "use_case": "session_quality",
            "ts": {"$gte": since},
        }

        # For demo data there is no org_id, but if you add it later this
        # will first try org-specific, then fall back to global demo.
        scores_docs = list(trainer_preds.find(q))
        if not scores_docs and org_id:
            q["org_id"] = org_id
            scores_docs = list(trainer_preds.find(q))

        scores = [
            p.get("score")
            for p in scores_docs
            if isinstance(p.get("score"), (int, float))
        ]
        if not scores:
            return "I don’t see any recent session scores logged in the last 7 days."
        avg = sum(scores) / len(scores)
        return f"The average session score over the last 7 days is {avg:.1f}/5."

    return (
        "I can help you see who’s most at risk and how sessions look. Try:\n"
        "• \"Who is high-risk right now?\"\n"
        "• \"How many athletes are low risk?\"\n"
        "• \"What’s the average session score in the last 7 days?\""
    )


# --------- MAIN ROUTER ---------


@router.post("/query")
def assistant_query(
    payload: AssistantQuery,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Simple rule-based org assistant. Uses the user's vertical / role
    plus optional UI context (X-MHD-Context) to decide which engine to call.
    """
    vertical = (user.get("vertical") or "").lower()
    role = (user.get("role") or "").lower()
    msg = payload.message or ""

    # Optional UI context from the frontend (trainer / org dashboards)
    context_header = request.headers.get("X-MHD-Context")
    try:
        ui_ctx = json.loads(context_header) if context_header else {}
    except Exception:
        ui_ctx = {}

    # Trainers always use the trainer engine
    if role in ("trainer", "staff"):
        answer = answer_trainer(msg, user, ui_ctx)

    # Org verticals
    elif vertical == "financial":
        answer = answer_financial(msg, user)
    elif vertical == "law":
        answer = answer_law(msg, user)
    elif vertical in ("oil_gas", "oil-gas", "oilgas"):
        answer = answer_oil(msg, user)

    else:
        # generic fallback
        answer = (
            "I can help interpret your MHD dashboards. Try asking things such as:\n"
            "• \"What looks most at risk right now?\"\n"
            "• \"What’s overdue in the next 7 days?\"\n"
            "• \"Where should I focus today?\""
        )

    return {"answer": answer}
