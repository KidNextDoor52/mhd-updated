from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.db import db
from app.auth import get_current_user

router = APIRouter(prefix="/weightroom", tags=["weightroom"])
templates = Jinja2Templates(directory="app/templates")

weightroom_collection = db.weightroom


@router.get("/", response_class=HTMLResponse)
async def weightroom_dashboard(request: Request, current_user: dict = Depends(get_current_user)):
    data = weightroom_collection.find_one({"username": current_user["username"]}) or {
        "username": current_user["username"],
        "bench": None,
        "squat": None,
        "vertical": None,
        "forty_dash": None,
        "first_time": True,
    }

    return templates.TemplateResponse("weightroom.html", {
        "request": request,
        "weightroom": data,
    })


@router.post("/update")
async def update_weightroom(
    request: Request,
    bench: str = Form(None),
    squat: str = Form(None),
    vertical: str = Form(None),
    forty_dash: str = Form(None),
    current_user: dict = Depends(get_current_user),
):
    weightroom_collection.update_one(
        {"username": current_user["username"]},
        {"$set": {
            "bench": bench,
            "squat": squat,
            "vertical": vertical,
            "forty_dash": forty_dash,
            "first_time": False,
        }},
        upsert=True,
    )
    return RedirectResponse("/weightroom", status_code=303)
