from fastapi import APIRouter, Request, UploadFile, File, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from app.db import db
from app.auth import get_current_user

router = APIRouter(prefix="/upload", tags=["upload"])
templates = Jinja2Templates(directory="app/templates")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

uploads_collection = db.uploads
upload_flags = db.upload_flags


@router.get("/", response_class=HTMLResponse)
async def upload_page(request: Request, current_user: dict = Depends(get_current_user)):
    files = list(uploads_collection.find({"username": current_user["username"]}))
    user_flag = upload_flags.find_one({"username": current_user["username"]}) or {"first_time": True}

    return templates.TemplateResponse("upload_record.html", {
        "request": request,
        "uploaded_files": files,
        "first_time": user_flag["first_time"],
    })


@router.post("/record")
async def upload_record(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)

    with open(path, "wb") as buffer:
        buffer.write(await file.read())

    uploads_collection.insert_one({
        "username": current_user["username"],
        "filename": filename,
        "upload_date": datetime.utcnow(),
    })

    upload_flags.update_one(
        {"username": current_user["username"]},
        {"$set": {"first_time": False}},
        upsert=True,
    )

    return RedirectResponse("/upload", status_code=303)
