from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.db import documents, medical_history
from app.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    tag: str = "",
    date: str = "",
    current_user: dict = Depends(get_current_user),
):
    """Dashboard showing documents + forms"""
    query = {}
    if tag:
        query["tags"] = {"$in": [tag.lower()]}
    if date:
        query["upload_date"] = {"$regex": f"^{date}"}

    docs = list(documents.find(query))
    forms = list(medical_history.find({"athlete_id": current_user["username"]}))

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "docs": docs, "forms": forms},
    )
