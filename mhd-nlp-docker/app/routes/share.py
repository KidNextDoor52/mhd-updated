from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta, timezone
from bson import ObjectId
import uuid

from app.db import db
from app.auth import get_current_user
from app.utils.logger import log_activity

router = APIRouter(prefix="/share", tags=["share"])
templates = Jinja2Templates(directory="app/templates")

uploads_col = db.uploads
shared_links = db.shared_links

def _utcnow():
    return datetime.now(timezone.utc)

# ---- keep your validate_shared_download(...) helper as-is ----

@router.get("/new", response_class=HTMLResponse)
def share_new(
    request: Request,
    file_id: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    file_doc = None
    if file_id:
        file_doc = uploads_col.find_one({"_id": ObjectId(file_id), "username": current_user["username"]})
        if not file_doc:
            raise HTTPException(status_code=404, detail="File not found")
    return templates.TemplateResponse(
        "share_new.html",
        {"request": request, "user": current_user, "file": file_doc, "preselected_id": file_id},
    )

@router.post("/new")
def share_new_post(
    request: Request,
    recipient_email: str = Form(...),
    expires_in_hours: int = Form(24),
    scope: str = Form("file"),                # "file" or "category"
    file_id: str | None = Form(None),
    categories: list[str] = Form([]),         # checkbox list
    current_user: dict = Depends(get_current_user),
):
    token = str(uuid.uuid4())
    recipient_email = recipient_email.lower().strip()

    allowed_file_ids: list[str] | None = None
    allowed_categories: list[str] = []

    if scope == "file":
        if not file_id:
            raise HTTPException(status_code=400, detail="file_id is required for file scope")
        f = uploads_col.find_one({"_id": ObjectId(file_id), "username": current_user["username"]})
        if not f:
            raise HTTPException(status_code=404, detail="File not found")
        allowed_file_ids = [str(f["_id"])]
    else:
        allowed_categories = [c.strip().lower() for c in categories if c.strip()]

    doc = {
        "token": token,
        "owner": current_user["username"],
        "recipient_email": recipient_email,
        "allowed_categories": allowed_categories,  # empty list = all categories
        "allowed_file_ids": allowed_file_ids or [],# non-empty => single-file scope
        "created_at": _utcnow(),
        "expires_at": _utcnow() + timedelta(hours=int(expires_in_hours)),
        "used_at": None,
    }
    shared_links.insert_one(doc)

    log_activity(
        current_user["username"],
        "create_share_link",
        {"recipient": recipient_email, "scope": scope, "categories": allowed_categories, "file_id": file_id},
    )


    return RedirectResponse(f"/share/{token}", status_code=303)

@router.get("/{token}", response_class=HTMLResponse)
def share_show(
    token: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    # Find link and ensure it belongs to the currently logged-in owner
    link = shared_links.find_one({"token": token, "owner": current_user["username"]})
    if not link:
        raise HTTPException(status_code=404, detail="Share link not found")

    # Build the list of files this link allows
    files = []
    if link.get("allowed_file_ids"):
        ids = [ObjectId(fid) for fid in link["allowed_file_ids"]]
        files = list(uploads_col.find({"_id": {"$in": ids}}))
    else:
        q = {"username": current_user["username"]}
        if link.get("allowed_categories"):
            q["category"] = {"$in": link["allowed_categories"]}
        files = list(uploads_col.find(q).sort("upload_date", -1).limit(50))

    # Precompute download URLs for convenience
    for f in files:
        f["download_url"] = f"/upload/download/{f['_id']}?token={token}&email={link['recipient_email']}"

    return templates.TemplateResponse(
        "share_success.html",
        {
            "request": request,
            "user": current_user,
            "token": token,
            "link": link,
            "files": files,
        },
    )