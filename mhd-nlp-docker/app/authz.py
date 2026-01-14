# app/authz.py
# app/authz.py
from __future__ import annotations

from typing import Callable, Optional
from fastapi import Depends, HTTPException, status

from app.auth import get_current_user


def require_role(*allowed_roles: str) -> Callable:
    """
    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("admin"))])
        async def admin_only(...):
            ...
    """
    allowed = set(r.strip().lower() for r in allowed_roles if r)

    def _dep(user: dict = Depends(get_current_user)) -> dict:
        role = (user.get("role") or "user").strip().lower()
        if role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return user

    return _dep


def require_org_user(user: dict = Depends(get_current_user)) -> dict:
    """
    Require the caller to be associated with an org_id.
    """
    if not user.get("org_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization access required",
        )
    return user


def require_vertical(*allowed_verticals: str) -> Callable:
    """
    Enforce that the user is in one of the allowed verticals (oil_gas, financial, law).
    """
    allowed = set(v.strip().lower() for v in allowed_verticals if v)

    def _dep(user: dict = Depends(get_current_user)) -> dict:
        vertical = (user.get("vertical") or "").strip().lower()
        if vertical not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Wrong vertical for this route",
            )
        return user

    return _dep
