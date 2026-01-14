# app/middleware/audit_middleware.py
from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.audit import write_audit_event


def _client_ip(request: Request) -> str:
    # Prefer X-Forwarded-For if present (ACA / proxies)
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Adds request_id + writes a baseline request audit record for denied/failed cases.
    (We do NOT log every request to avoid noise/cost; we log security-relevant outcomes.)

    It also attaches request_id to response headers for correlation.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        except Exception as e:
            # Unhandled exception -> audit as server_error
            write_audit_event(
                action="server_error",
                ok=False,
                actor=getattr(request.state, "actor", None),
                err=repr(e),
                meta={},
                request_ctx={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "ip": _client_ip(request),
                    "ua": request.headers.get("user-agent", ""),
                },
            )
            raise

        # Correlate
        response.headers["x-request-id"] = request_id

        # If auth/permission issues, log centrally (routes can still log richer events)
        if response.status_code in (401, 403):
            write_audit_event(
                action="permission_denied" if response.status_code == 403 else "auth_missing_or_invalid",
                ok=False,
                actor=getattr(request.state, "actor", None),
                err=f"HTTP {response.status_code}",
                meta={},
                request_ctx={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "ip": _client_ip(request),
                    "ua": request.headers.get("user-agent", ""),
                },
            )

        return response
