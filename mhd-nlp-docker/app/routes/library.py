# app/routes/library.py
from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.db import db

router = APIRouter(prefix="/api", tags=["library"])

@router.get("/library")
def list_library(current_user: dict = Depends(get_current_user)):
    items = list(db.education.find({}).sort("order", 1))
    return {"items": items}
