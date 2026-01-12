# app/authz.py
from fastapi import Depends, HTTPException
from typing import Literal
from app.auth import get_current_user  # sync dep returning {"_id","username","role"}

def require_role(role: Literal["viewer", "trainer", "admin"]):
    def _dep(user=Depends(get_current_user)):
        user_role = user.get("role", "user")
        allowed = {
            "viewer": {"viewer", "trainer", "admin", "user"},
            "trainer": {"trainer", "admin"},
            "admin": {"admin"},
        }[role]

        if user_role not in allowed:
            raise HTTPException(status_code=403, detail=f"requires {role} role")

        return user

    return _dep
