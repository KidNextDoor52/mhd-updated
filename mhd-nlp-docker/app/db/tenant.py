# app/db/tenant.py
from __future__ import annotations

from typing import Any, Dict


def enforce_tenant_filter(tenant_id: str, base_filter: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Hard rule: every query must include tenant_id.
    """
    if not tenant_id:
        raise ValueError("tenant_id required")
    f = dict(base_filter or {})
    # Do NOT allow callers to override tenant_id
    f["tenant_id"] = tenant_id
    return f


def with_tenant_doc(tenant_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hard rule: every inserted doc must include tenant_id.
    """
    if not tenant_id:
        raise ValueError("tenant_id required")
    d = dict(doc)
    d["tenant_id"] = tenant_id
    return d
