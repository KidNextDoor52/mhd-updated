# app/middleware/auth_context.py
from __future__ import annotations

from jose import JWTError, jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.settings import settings


class ClaimsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
            try:
                if settings.JWT_SECRET:
                    claims = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
                    request.state.claims = claims
            except JWTError:
                pass

        return await call_next(request)
