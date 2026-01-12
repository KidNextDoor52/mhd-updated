# app/auth.py
from datetime import datetime, timedelta, timezone
import os
import uuid
from typing import Optional

from fastapi import HTTPException, status, Request
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
from bson import ObjectId

from .db import db, users  # <--- PyMongo sync collections

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MIN", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
REFRESH_TOKEN_COOKIE = os.getenv("REFRESH_TOKEN_COOKIE", "mhd_refresh_token")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Collections (PyMongo)
refresh_tokens = db["refresh_tokens"]
revoked_tokens = db["revoked_tokens"]

# ---------- password helpers ----------

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ---------- user lookup (sync) ----------

def get_user_by_login(login: str) -> Optional[dict]:
    """
    Login can be username or email (case-insensitive for email).

    This is written for PyMongo (sync). If at some point `users` becomes an
    async Motor collection, callers should wrap it, not this function.
    """
    login = (login or "").strip()
    return users.find_one({
        "$or": [
            {"username": login},
            {"email": login.lower()},
        ]
    })


# ---------- main auth helper (SYNC) ----------

def authenticate_user(login: str, password: str) -> Optional[dict]:
    """
    Synchronous: used by /auth/token

    Also robust to the case where get_user_by_login (or its underlying collection)
    accidentally returns a coroutine/Future instead of a dict.
    """
    import asyncio

    user = get_user_by_login(login)

    # If somehow a coroutine/Future is returned, resolve it here
    if asyncio.iscoroutine(user) or isinstance(user, asyncio.Future):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop = asyncio.get_event_loop()
        user = loop.run_until_complete(user)

    # Now expect a dict (or None)
    if not user or not isinstance(user, dict) or not user.get("password"):
        return None

    if not verify_password(password, user["password"]):
        return None

    return user


# ---------- JWT helpers ----------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _create_jwt(sub: str, token_type: str, expires_delta: timedelta) -> str:
    iat = _now_utc()
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
        {"$set": {
            "jti": payload["jti"],
            "sub": payload["sub"],
            "exp": payload["exp"],
            "revoked": False,
            "created_at": _now_utc(),
        }},
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
        {"$set": {"jti": jti, "sub": sub, "exp": exp, "reason": reason}},
        upsert=True,
    )


# ---------- dependencies for routes ----------

def get_current_user(request: Request) -> dict:
    """
    Pull access token from auth (Bearer or from 'token' cookie.)
    Sync dependency; FastAPI will run it in threadpool automaticall.
    """
    token = None

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    # Cookie Fallback
    if not token:
        token = request.cookies.get("token")

    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Wrong token type")
    
    if is_revoked(payload["jti"]):
        raise HTTPException(status_code=401, detail="Token has been revoked")
    
    try:
        u = users.find_one({"_id": ObjectId(payload["sub"])})
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid subject")
    
    if not u:
        raise HTTPException(status_code=401, detail="User not found")
    

    # dashboard dispatcher dependencies
    return {
        "_id": str(u["_id"]),
        "username": u.get("username"),
        "role": u.get("role", "user"),
        "email": u.get("email"),
        "vertical": u.get("vertical"),
        "org_id": u.get("org_id"),
        "demo": u.get("demo", False)
    }

def get_current_user_optional(request: Request) -> Optional[dict]:
    """
    Same as get_current_user, but returns None instead of raising if unauthenticated.
    """
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

        return {
            "_id": str(u["_id"]),
            "username": u.get("username"),
            "role": u.get("role", "user"),
            "email": u.get("email"),
            "vertical": u.get("vertical"),   # <-- added
            "org_id": u.get("org_id"),       # <-- added
            "demo": u.get("demo", False),
        }
    except Exception:
        return None
