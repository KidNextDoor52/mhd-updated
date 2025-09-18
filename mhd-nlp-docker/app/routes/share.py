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


# ---------------------------
# Create form (GET /share/new)
# ---------------------------
@router.get("/new", response_class=HTMLResponse)
def share_new(
    request: Request,
    file_id: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    file_doc = None
    preselected_id = None

    # If we were called as /share/new?file_id=..., try to load that file
    if file_id:
        try:
            oid = ObjectId(file_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid file id")

        file_doc = uploads_col.find_one({"_id": oid, "username": current_user["username"]})
        if not file_doc:
            raise HTTPException(status_code=404, detail="File not found or not yours")
        preselected_id = str(file_doc["_id"])

    # Build a de-duplicated list (latest per filename) only when nothing is preselected
    uploaded_files = []
    if not preselected_id:
        uploaded_files = list(uploads_col.aggregate([
            {"$match": {"username": current_user["username"]}},
            {"$sort": {"upload_date": -1}},                    # newest first
            {"$group": {"_id": "$filename", "doc": {"$first": "$$ROOT"}}},
            {"$replaceWith": "$doc"},
            {"$sort": {"filename": 1}},
        ]))

    return templates.TemplateResponse(
        "share_new.html",
        {
            "request": request,
            "user": current_user,
            "file": file_doc,
            "preselected_id": preselected_id,
            "uploaded_files": uploaded_files,  # used by the template select
        },
    )


# ----------------------------
# Create link (POST /share/new)
# ----------------------------
@router.post("/new")
def share_new_post(
    request: Request,
    recipient_email: str = Form(...),
    expires_in_hours: int = Form(24),
    scope: str = Form("file"),                  # "file" or "category"
    file_id: str | None = Form(None),           # legacy single
    file_ids: list[str] = Form([]),             # NEW: multi-pick
    categories: list[str] = Form([]),           # checkboxes
    current_user: dict = Depends(get_current_user),
):
    token = str(uuid.uuid4())
    recipient_email = recipient_email.lower().strip()

    allowed_file_ids: list[str] = []
    allowed_categories: list[str] = []

    if scope == "file":
        # merge hidden single + multi-select
        candidate_ids = [fid for fid in ([file_id] + file_ids) if fid]
        if not candidate_ids:
            raise HTTPException(status_code=400, detail="No file selected")

        # validate ownership
        owned: list[str] = []
        for fid in candidate_ids:
            try:
                doc = uploads_col.find_one({"_id": ObjectId(fid), "username": current_user["username"]})
                if doc:
                    owned.append(str(doc["_id"]))
            except Exception:
                pass
        if not owned:
            raise HTTPException(status_code=404, detail="Selected file(s) not found")
        allowed_file_ids = sorted(set(owned))
    else:
        allowed_categories = [c.strip().lower() for c in categories if c.strip()]

    shared_links.insert_one({
        "token": token,
        "owner": current_user["username"],
        "recipient_email": recipient_email,
        "allowed_categories": allowed_categories,   # [] = all
        "allowed_file_ids": allowed_file_ids,       # non-empty => file scope
        "created_at": _utcnow(),
        "expires_at": _utcnow() + timedelta(hours=int(expires_in_hours)),
        "used_at": None,
    })

    log_activity(
        current_user["username"],
        "create_share_link",
        {"recipient": recipient_email, "scope": scope,
         "categories": allowed_categories, "file_ids": allowed_file_ids},
    )

    return RedirectResponse(f"/share/{token}", status_code=303)


# --------------------------------
# Show a link you just created (UI)
# --------------------------------
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
