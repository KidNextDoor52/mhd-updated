from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.db import db
from app.auth import get_current_user
from app.utils.logger import log_activity

router = APIRouter(prefix="/training", tags=["training"])
templates = Jinja2Templates(directory="app/templates")

training_collection = db.training
training_flags = db.training_flags


@router.get("/", response_class=HTMLResponse)
async def training_page(request: Request, current_user: dict = Depends(get_current_user)):
    records = list(training_collection.find({"username": current_user["username"]}))
    user_flag = training_flags.find_one({"username": current_user["username"]}) or {"first_time": True}

    return templates.TemplateResponse("training_room.html", {
        "request": request,
        "records": records,
        "training": user_flag,
    })


@router.post("/update")
async def update_training(
    request: Request,
    injury: str = Form(...),
    details: str = Form(...),
    current_user: dict = Depends(get_current_user),
):
    record = {
        "username": current_user["username"],
        "injury": injury,
        "details": details,
    }
    training_collection.insert_one(record)

    training_flags.update_one(
        {"username": current_user["username"]},
        {"$set": {"first_time": False}},
        upsert=True,
    )

    log_activity(
        user_id=current_user["username"],
        action="add_training_log",
        metadata=record
    )

    return RedirectResponse("/training", status_code=303)

