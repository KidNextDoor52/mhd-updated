from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.security import OAuth2PasswordRequestForm
from app.db import users
from app.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup")
def signup(username: str = Form(...), password: str = Form(...)):
    """Register a new user"""
    if users.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="Username already taken")

    hashed_password = get_password_hash(password)
    user = {"username": username, "password": hashed_password}
    users.insert_one(user)
    return {"message": "User created"}


@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and return JWT token"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token({"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def profile(current_user: dict = Depends(get_current_user)):
    """Return current user info"""
    return {
        "username": current_user["username"],
        "role": current_user.get("role", "user"),
    }
