# app/auth.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import uuid
from typing import Optional

from fastapi import HTTPException, status, Request
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
from bson import ObjectId

from .db import db, users  # PyMongo sync collections
from app.utils.audit import write_audit_event

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MIN", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
REFRESH_TOKEN_COOKIE = os.getenv("REFRESH_TOKEN_COOKIE", "mhd_refresh_token")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

refresh_tokens = db["refresh_tokens"]
revoked_tokens = db["revoked_tokens"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _request_ctx(request: Optional[Request]) -> dict:
    if not request:
        return {}
    return {
        "request_id": getattr(request.state, "request_id", None),
        "method": request.method,
        "path": request.url.path,
        "ip": request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else ""),
        "ua": request.headers.get("user-agent", ""),
    }


# ---------- password helpers ----------
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------- user lookup (sync) ----------
def get_user_by_login(login: str) -> Optional[dict]:
    login = (login or "").strip()
    return users.find_one(
        {
            "$or": [
                {"username": login},
                {"email": login.lower()},
            ]
        }
    )


# ---------- main auth helper (SYNC) ----------
def authenticate_user(login: str, password: str, request: Optional[Request] = None) -> Optional[dict]:
    """
    Validates credentials. Emits audit events for failures/success.
    """
    import asyncio

    user = get_user_by_login(login)

    if asyncio.iscoroutine(user) or isinstance(user, asyncio.Future):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop = asyncio.get_event_loop()
        user = loop.run_until_complete(user)

    if not user or not isinstance(user, dict) or not user.get("password"):
        write_audit_event(
            action="login_failed",
            ok=False,
            actor={"username": login},
            err="User not found or missing password",
            meta={"login": login},
            request_ctx=_request_ctx(request),
            source="web" if request else "api",
        )
        return None

    if not verify_password(password, user["password"]):
        write_audit_event(
            action="login_failed",
            ok=False,
            actor={"_id": str(user.get("_id")), "username": user.get("username"), "role": user.get("role"), "email": user.get("email")},
            err="Invalid password",
            meta={"login": login},
            request_ctx=_request_ctx(request),
            source="web" if request else "api",
        )
        return None

    write_audit_event(
        action="login_success",
        ok=True,
        actor={"_id": str(user.get("_id")), "username": user.get("username"), "role": user.get("role"), "email": user.get("email")},
        meta={"login": login},
        request_ctx=_request_ctx(request),
        source="web" if request else "api",
    )
    return user


# ---------- JWT helpers ----------
def _create_jwt(sub: str, token_type: str, expires_delta: timedelta) -> str:
    iat = _utcnow()
    exp = iat + expires_delta
    jti = str(uuid.uuid4())
    payload = {
        "sub": sub,
        "type": token_type,
        "jti": jti,
        "iat": int(iat.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(sub: str) -> str:
    return _create_jwt(sub, "access", timedelta(minutes=ACCESS_TOKEN_EXPIRE_MIN))


def create_refresh_token(sub: str) -> str:
    token = _create_jwt(sub, "refresh", timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    refresh_tokens.update_one(
        {"jti": payload["jti"]},
        {
            "$set": {
                "jti": payload["jti"],
                "sub": payload["sub"],
                "exp": payload["exp"],
                "revoked": False,
                "created_at": _utcnow(),
            }
        },
        upsert=True,
    )
    return token


def decode_token(raw: str) -> dict:
    try:
        return jwt.decode(raw, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def is_revoked(jti: str) -> bool:
    return revoked_tokens.find_one({"jti": jti}) is not None


def revoke_token(jti: str, sub: str, exp: int, reason: str = "logout") -> None:
    revoked_tokens.update_one(
        {"jti": jti},
        {"$set": {"jti": jti, "sub": sub, "exp": exp, "reason": reason, "revoked_at": _utcnow()}},
        upsert=True,
    )
    write_audit_event(
        action="token_revoked",
        ok=True,
        actor={"user_id": sub},
        meta={"jti": jti, "reason": reason, "exp": exp},
        source="api",
    )


# ---------- dependencies for routes ----------
def get_current_user(request: Request) -> dict:
    token = None

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    if not token:
        token = request.cookies.get("token")

    if not token:
        write_audit_event(
            action="auth_missing_or_invalid",
            ok=False,
            actor=None,
            err="Missing authentication token",
            meta={},
            request_ctx=_request_ctx(request),
        )
        raise HTTPException(status_code=401, detail="Missing authentication token")

    payload = decode_token(token)

    if payload.get("type") != "access":
        write_audit_event(
            action="auth_missing_or_invalid",
            ok=False,
            actor=None,
            err="Wrong token type",
            meta={"type": payload.get("type")},
            request_ctx=_request_ctx(request),
        )
        raise HTTPException(status_code=401, detail="Wrong token type")

    if is_revoked(payload["jti"]):
        write_audit_event(
            action="auth_missing_or_invalid",
            ok=False,
            actor=None,
            err="Token revoked",
            meta={"jti": payload.get("jti")},
            request_ctx=_request_ctx(request),
        )
        raise HTTPException(status_code=401, detail="Token has been revoked")

    try:
        u = users.find_one({"_id": ObjectId(payload["sub"])})
    except Exception:
        write_audit_event(
            action="auth_missing_or_invalid",
            ok=False,
            actor=None,
            err="Invalid subject",
            meta={"sub": payload.get("sub")},
            request_ctx=_request_ctx(request),
        )
        raise HTTPException(status_code=401, detail="Invalid subject")

    if not u:
        write_audit_event(
            action="auth_missing_or_invalid",
            ok=False,
            actor=None,
            err="User not found",
            meta={"sub": payload.get("sub")},
            request_ctx=_request_ctx(request),
        )
        raise HTTPException(status_code=401, detail="User not found")

    actor = {
        "_id": str(u["_id"]),
        "username": u.get("username"),
        "role": u.get("role", "user"),
        "email": u.get("email"),
        "vertical": u.get("vertical"),
        "org_id": u.get("org_id"),
        "demo": u.get("demo", False),
    }

    # Attach for middleware correlation (optional)
    request.state.actor = actor
    return actor


def get_current_user_optional(request: Request) -> Optional[dict]:
    try:
        token = request.cookies.get("token")
        if not token:
            auth = request.headers.get("Authorization") or ""
            if auth.lower().startswith("bearer "):
                token = auth.split(" ", 1)[1].strip()

        if not token:
            return None

        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        if is_revoked(payload["jti"]):
            return None

        u = users.find_one({"_id": ObjectId(payload["sub"])})
        if not u:
            return None

        actor = {
            "_id": str(u["_id"]),
            "username": u.get("username"),
            "role": u.get("role", "user"),
            "email": u.get("email"),
            "vertical": u.get("vertical"),
            "org_id": u.get("org_id"),
            "demo": u.get("demo", False),
        }
        request.state.actor = actor
        return actor
    except Exception:
        return None
