# app/utils/audit.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.db import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Actor:
    """Normalized identity for audit events."""
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    org_id: Optional[str] = None
    vertical: Optional[str] = None

    @staticmethod
    def from_user(user: Optional[dict]) -> "Actor":
        if not user:
            return Actor()
        return Actor(
            user_id=str(user.get("_id")) if user.get("_id") is not None else None,
            username=user.get("username"),
            role=user.get("role"),
            email=user.get("email"),
            org_id=user.get("org_id"),
            vertical=user.get("vertical"),
        )

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "email": self.email,
            "org_id": self.org_id,
            "vertical": self.vertical,
        }


def ensure_audit_indexes() -> None:
    """
    Call this once at app startup (NOT at import time).

    Creates indexes needed for searching/retention.
    """
    events = db["audit_events"]
    events.create_index([("ts", 1)])
    events.create_index([("action", 1)])
    events.create_index([("ok", 1)])
    events.create_index([("actor.username", 1)])
    events.create_index([("request.request_id", 1)])


def write_audit_event(
    *,
    action: str,
    ok: bool,
    actor: Optional[dict] = None,
    err: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    source: str = "api",
    request_ctx: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Write one normalized audit event. Best-effort (never raises).

    Event schema:
    {
      ts, action, ok, err,
      actor: {user_id, username, role, email, org_id, vertical},
      meta: {...},
      source: "api"|"web"|"job",
      request: {request_id, method, path, ip, ua}
    }
    """
    try:
        events = db["audit_events"]
        doc = {
            "ts": _utcnow(),
            "action": action,
            "ok": ok,
            "err": err,
            "actor": Actor.from_user(actor).to_dict(),
            "meta": meta or {},
            "source": source,
            "request": request_ctx or {},
        }
        events.insert_one(doc)
    except Exception:
        # Never block requests due to audit failure.
        pass
