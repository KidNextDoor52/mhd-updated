from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from datetime import datetime, timezone
from app.db import users
from app.auth import (
    create_access_token,
    create_refresh_token,
    REFRESH_TOKEN_COOKIE,
    COOKIE_SECURE,
)

import os

router = APIRouter(prefix="/auth/google", tags=["auth-google"])

#Load config from env (.env.dev, .env.prod, etc.)
config = Config(environ=os.environ)

oauth = OAuth(config)

#Register google OAuth2
oauth.register(
    name="google",
    client_id=config("GOOGLE_CLIENT_ID"),
    client_secret=config("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@router.get("/login")
async def login_via_google(request: Request):
    """
    step 1: Redirect user to Google's consent page
    """
    redirect_uri = request.url_for("auth_via_google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/callback")
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

    
    access_token = create_access_token({"sub": str(user["_id"]), "username": username})
    refresh_token = create_refresh_token({"sub": str(user["_id"]), "username": username})

    resp = RedirectResponse(url="/dashboard")
    resp.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,   # keep refresh token server-only
        secure=COOKIE_SECURE,
        samesite="lax",
    )
    resp.set_cookie("token", access_token, httponly=False, samesite="lax")  # access for JS
    return resp