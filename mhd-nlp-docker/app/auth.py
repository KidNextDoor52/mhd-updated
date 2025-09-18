# app/auth.py
from datetime import datetime, timedelta, timezone
import os
import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
from bson import ObjectId
import re
from .db import db, users  # your existing db handle + users collection

# --- env & crypto ------------------------------------------------------------
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = os.getenv("JWT_ALG", "HS256")

ACCESS_TOKEN_EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MIN", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

REFRESH_TOKEN_COOKIE = os.getenv("REFRESH_TOKEN_COOKIE", "mhd_refresh_token")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"   # set true in production (HTTPS)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# --- collections -------------------------------------------------------------
revoked_tokens = db["revoked_tokens"]      # { jti, sub, exp, reason }
refresh_tokens = db["refresh_tokens"]      # { jti, sub, exp, revoked:bool, created_at }

# helpful indexes (idempotent)
users.create_index("username", unique=True)
refresh_tokens.create_index("exp")
revoked_tokens.create_index("exp")

# --- password utils ----------------------------------------------------------
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# --- user lookup -------------------------------------------------------------
def get_user_by_username(username: str) -> Optional[dict]:
    return users.find_one({"username": username})

def get_user_by_login(login: str) -> Optional[dict]:
    """Login can be either username or email."""
    login = (login or "").strip()        # <-- trim whitespace
    return users.find_one({
        "$or": [
            {"username": login},         # exact match for username
            {"email": login.lower()},    # lowercase for email
        ]
    })

# --- JWT helpers -------------------------------------------------------------
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
        "exp": int(exp.timestamp())
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_access_token(sub: str) -> str:
    return _create_jwt(sub, "access", timedelta(minutes=ACCESS_TOKEN_EXPIRE_MIN))

def create_refresh_token(sub: str) -> str:
    token = _create_jwt(sub, "refresh", timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    # persist jti for server-side control
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    refresh_tokens.insert_one({
        "jti": payload["jti"],
        "sub": payload["sub"],
        "exp": payload["exp"],
        "revoked": False,
        "created_at": _now_utc()
    })
    return token

def decode_token(raw: str) -> dict:
    try:
        return jwt.decode(raw, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

def is_revoked(jti: str) -> bool:
    return revoked_tokens.find_one({"jti": jti}) is not None

def revoke_token(jti: str, sub: str, exp: int, reason: str = "logout") -> None:
    # upsert so double-logout is harmless
    revoked_tokens.update_one(
        {"jti": jti},
        {"$set": {"jti": jti, "sub": sub, "exp": exp, "reason": reason}},
        upsert=True,
    )

# --- dependency used by your routes -----------------------------------------

def get_current_user(request: Request) -> dict:
    """
    Pull token from Authorization header (Bearer) OR from 'token' cookie.
    """
    # 1) Try Authorization header
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    # 2) Fallback to cookie
    if not token:
        token = request.cookies.get("token")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token")

    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type")
    if is_revoked(payload["jti"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    sub = payload.get("sub")
    try:
        user = users.find_one({"_id": ObjectId(sub)})
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid subject")
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {"username": user["username"], "role": user.get("role", "user")}

from typing import Optional  # already present
from fastapi import Request  # already present

def get_current_user_optional(request: Request) -> Optional[dict]:
    """
    Best-effort auth:
    - If a valid access token is present (cookie or Authorization header), return a user dict.
    - If not present/invalid, return None instead of raising.
    """
    # Try cookie first
    token = request.cookies.get("token")

    # Fallback to Authorization: Bearer <token>
    if not token:
        auth = request.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()

    if not token:
        return None

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        if is_revoked(payload["jti"]):
            return None

        sub = payload.get("sub")
        if not sub:
            return None

        u = users.find_one({"_id": ObjectId(sub)})
        if not u:
            return None

        return {
            "_id": str(u["_id"]),
            "username": u.get("username"),
            "email": u.get("email"),
            "role": u.get("role", "user"),
        }
    except Exception:
        return None

# --- simple auth helper for router ------------------------------------------
def authenticate_user(login: str, password: str) -> Optional[dict]:
    user = get_user_by_login(login)
    # If the user has no password (e.g., Google-only), reject password login.
    if not user or not user.get("password"):
        return None
    if not verify_password(password, user["password"]):
        return None
    return user
