# app/middleware/security_headers.py
from __future__ import annotations

from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds baseline security headers.
    Safe defaults for an API + Jinja templates.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)

        # Baseline hardening
        response.headers.setdefault("x-content-type-options", "nosniff")
        response.headers.setdefault("x-frame-options", "DENY")
        response.headers.setdefault("referrer-policy", "no-referrer")
        response.headers.setdefault("permissions-policy", "geolocation=(), microphone=(), camera=()")

        # CSP: allow self + inline styles/scripts if needed by templates (tighten later)
        # If you serve 3rd-party JS, update this accordingly.
        response.headers.setdefault(
            "content-security-policy",
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )

        return response
