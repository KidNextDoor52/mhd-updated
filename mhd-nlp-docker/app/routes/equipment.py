from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.db import db
from app.auth import get_current_user
from app.utils.logger import log_activity

router = APIRouter(prefix="/equipment", tags=["equipment"])
templates = Jinja2Templates(directory="app/templates")

equipment_collection = db.equipment


@router.get("/", response_class=HTMLResponse)
async def show_equipment_room(
    request: Request, current_user: dict = Depends(get_current_user)
):
    equipment_data = (
        equipment_collection.find_one({"username": current_user["username"]}) or {}
    )
    first_time = not bool(equipment_data)
    return templates.TemplateResponse(
        "equipment_room.html",
        {
            "request": request,
            "user": current_user,
            "equipment": equipment_data,
            "show_video": first_time,
        },
    )


@router.get("/form", response_class=HTMLResponse)
async def show_equipment_form(
    request: Request, current_user: dict = Depends(get_current_user)
):
    existing = equipment_collection.find_one({"username": current_user["username"]})
    return templates.TemplateResponse(
        "equipment_form.html",
        {
            "request": request,
            "equipment": existing or {},
            "editing": bool(existing),
        },
    )


@router.post("/form")
async def submit_equipment_form(
    request: Request,
    cleats: str = Form(...),
    cleats_size: str = Form(...),
    helmet: str = Form(...),
    helmet_size: str = Form(...),
    shoulder_pads: str = Form(...),
    pads_size: str = Form(...),
    mouthpiece: str = Form(...),
    gloves: str = Form(...),
    contacts: str = Form(...),
    measurement: str = Form(...),
    current_user: dict = Depends(get_current_user),
):
    equipment_doc = {
        "username": current_user["username"],
        "items": [
            {"category": "cleats", "brand": cleats, "size": cleats_size, "notes": ""},
            {"category": "helmet", "brand": helmet, "size": helmet_size, "notes": ""},
            {
                "category": "shoulder_pads",
                "brand": shoulder_pads,
                "size": pads_size,
                "notes": "",
            },
            {"category": "mouthpiece", "brand": mouthpiece, "notes": ""},
            {"category": "gloves", "brand": gloves, "notes": ""},
            {"category": "contacts", "brand": contacts, "notes": ""},
        ],
        "measurement": measurement,
    }

    equipment_collection.update_one(
        {"username": current_user["username"]},
        {"$set": equipment_doc},
        upsert=True,
    )

    log_activity(
        user_id=current_user["username"],
        action="update_equipment",
        metadata={"items": equipment_doc["items"]},
    )

    return RedirectResponse("/equipment", status_code=303)
