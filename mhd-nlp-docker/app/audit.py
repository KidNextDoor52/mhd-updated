# app/audit.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import Request

from app.db import db


def write_audit_event(
    *,
    tenant_id: Optional[str],
    user_id: str,
    action: str,
    outcome: str = "success",
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> None:
    """
    Append-only audit log (PyMongo / sync).
    - Never raises (audit failures should not break requests)
    - Durable, simple schema
    """
    try:
        doc: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "action": action,
            "outcome": outcome,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "extra": extra or {},
        }

        if request is not None:
            doc["ip"] = request.client.host if request.client else None
            doc["user_agent"] = request.headers.get("user-agent")

        db["audit_events"].insert_one(doc)
    except Exception:
        # Never block app behavior due to audit logging
        pass


# Backwards-compatible alias (if any code still imports log_event)
def log_event(user: str, action: str, details: Optional[Dict[str, Any]] = None) -> None:
    write_audit_event(
        tenant_id=None,
        user_id=user or "anonymous",
        action=action,
        extra=details or {},
    )
