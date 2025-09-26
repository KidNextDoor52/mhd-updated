# app/routes/forms.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timezone

from app.auth import get_current_user
from app.db import db

router = APIRouter(prefix="/forms", tags=["forms"])
templates = Jinja2Templates(directory="app/templates")
UTC = timezone.utc

@router.get("/", response_class=HTMLResponse)
def list_forms(request: Request, current_user: dict = Depends(get_current_user)):
    forms = list(db.forms.find({}).sort("title", 1))
    answers = list(
        db.form_answers
          .find({"user": current_user["username"]})
          .sort("submitted_at", -1)
          .limit(20)
    )
    return templates.TemplateResponse(
        "forms.html",
        {"request": request, "forms": forms, "answers": answers}
    )

@router.get("/{slug}", response_class=HTMLResponse)
def fill_form(slug: str, request: Request, current_user: dict = Depends(get_current_user)):
    form = db.forms.find_one({"slug": slug})
    if not form:
        return HTMLResponse("Form not found", status_code=404)
    return templates.TemplateResponse("form_fill.html", {"request": request, "form": form})

@router.post("/{slug}")
async def submit_form(
    slug: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    form = db.forms.find_one({"slug": slug})
    if not form:
        return RedirectResponse("/forms?err=missing", status_code=303)

    # await is valid because this is async def
    formdata = await request.form()
    data = dict(formdata.items())

    db.form_answers.insert_one({
        "user": current_user["username"],
        "form_slug": slug,
        "answers": data,
        "submitted_at": datetime.now(UTC),
    })
    db.events.insert_one({
        "user": current_user["username"],
        "type": "form_submitted",
        "date": datetime.now(UTC),
        "source": "web",
        "summary": f"Submitted form: {form.get('title') or slug}",
        "tags": [slug],
    })
    return RedirectResponse("/forms?msg=submitted", status_code=303)
