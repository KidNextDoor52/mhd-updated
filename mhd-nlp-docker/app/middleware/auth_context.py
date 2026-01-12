# app/middleware/auth_context.py
from __future__ import annotations

from jose import JWTError, jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.settings import settings  # adjust if settings object name differs


class ClaimsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only attach claims if bearer token exists; otherwise continue
        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
            try:
                claims = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
                request.state.claims = claims
            except JWTError:
                # leave claims unset; endpoints will 401 when require_auth is used
                pass

        return await call_next(request)
