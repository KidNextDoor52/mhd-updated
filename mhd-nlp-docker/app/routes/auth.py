# app/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, Form, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from datetime import datetime, timezone
import os, uuid
from app.auth import revoke_token, decode_token, REFRESH_TOKEN_COOKIE

from app.db import users, db
from app.auth import (
    authenticate_user,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    REFRESH_TOKEN_COOKIE,
)
from app.utils.logger import log_activity

router = APIRouter(prefix="/auth", tags=["auth"])

# --- OAuth Setup (Google) ---
config = Config(environ=os.environ)
oauth = OAuth(config)

oauth.register(
    name="google",
    client_id=config("GOOGLE_CLIENT_ID"),
    client_secret=config("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# ---------- Signup ----------
@router.post("/signup", status_code=201)
def signup(username: str = Form(...), password: str = Form(...), email: str = Form(...)):
    if users.find_one({"username": username}):
        raise HTTPException(status_code=409, detail="Username already exists")
    if users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email already registered")

    doc = {
        "username": username,
        "email": email,
        "password": get_password_hash(password),
        "role": "user",
        "created_at": datetime.now(timezone.utc),
    }
    users.insert_one(doc)

    log_activity(user_id=username, action="signup", metadata={"email": email})
    return {"message": "User created"}

# ---------- Username/Password Login ----------
@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    sub = str(user["_id"])  # must be string for JWT
    access_token = create_access_token(sub)
    refresh_token = create_refresh_token(sub)

    log_activity(user_id=user["username"], action="login_password", metadata={})

    # Return tokens in JSON for frontend, AND set cookies for auto-login
    resp = JSONResponse({
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
    })
    resp.set_cookie(
        key="token",
        value=access_token,
        httponly=False,   # True in prod (set False if you want JS access)
        samesite="lax"
    )
    resp.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,    # keep refresh token server-only
        samesite="lax"
    )
    return resp

# ---------- Google Login ----------
@router.get("/google/login")
async def login_via_google(request: Request):
    redirect_uri = request.url_for("auth_via_google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def auth_via_google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to retrieve Google user info")

    email = user_info["email"]
    username = user_info.get("name", email.split("@")[0])

    user = users.find_one({"email": email})
    if not user:
        user_doc = {
            "username": username,
            "email": email,
            "provider": "google",
            "created_at": datetime.now(timezone.utc),
            "role": "user",
        }
        users.insert_one(user_doc)
        user = user_doc

    log_activity(user_id=username, action="login_google", metadata={"email": email})

    sub = str(user["_id"])
    access_token = create_access_token(sub)
    refresh_token = create_refresh_token(sub)

    resp = RedirectResponse(url="/dashboard")
    resp.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=False,  # toggle True in prod
        samesite="lax",
    )
    resp.set_cookie("token", access_token, httponly=False, samesite="lax")
    return resp

# ---------- Forgot Password ----------
@router.post("/forgot-password")
def forgot_password(email: str = Form(...)):
    user = users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")

    token = str(uuid.uuid4())
    db.password_resets.insert_one({
        "email": email,
        "token": token,
        "created_at": datetime.now(timezone.utc)
    })

    # TODO: actually send email in production
    print(f"[DEBUG] Password reset token for {email}: {token}")

    return {"message": "Password reset requested. Check your email for reset instructions."}

# ---------- Reset Password ----------
@router.post("/reset-password")
def reset_password(token: str = Form(...), new_password: str = Form(...)):
    reset = db.password_resets.find_one({"token": token})
    if not reset:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    users.update_one(
        {"email": reset["email"]},
        {"$set": {"password": get_password_hash(new_password)}}
    )
    db.password_resets.delete_one({"_id": reset["_id"]})

    return {"message": "Password updated successfully"}

#========== Loguot --------
@router.post("/logout")
def logout(request: Request, response: Response):
    #revoke refresh token if present
    rt = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if rt:
        try:
            p = decode_token(rt)
            revoke_token(p["jti"], p["sub"], p["exp"], reason="logout")
        except Exception:
            pass

    # clear cookies
    response = JSONResponse({"message": "Logged Out"})
    response.delete_cookie("token")
    response.delete_cookie(REFRESH_TOKEN_COOKIE)
    return response