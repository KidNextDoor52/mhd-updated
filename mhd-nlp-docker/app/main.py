# app/main.py
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.db.storage import ensure_buckets, storage_startup
from app.db_init import ensure_indexes
from app.middleware.auth_context import ClaimsMiddleware
from app.monitoring.middleware import APIMetricsMiddleware

from app.routes.pipeline import router as pipeline_router
from app.routes.predict import router as predict_router
from app.routes.pipeline_ingest import router as pipeline_ingest_router
from app.routes.pipeline_async import router as pipeline_async_router
from app.routes.models import router as models_router

from app.routes import (
    auth,
    equipment,
    weightroom,
    upload,
    training,
    dashboard,
    auth_google,
    profile,
    share,
    metrics,
    trainer_dashboard,
    summary,
    forms,
    connect,
    org_financial,
    org_law,
    org_oil,
    assistant,
)

app = FastAPI()

# Static + templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Middleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", os.getenv("SECRET_KEY", "dev")))
app.add_middleware(APIMetricsMiddleware)
app.add_middleware(ClaimsMiddleware)

# Routers
app.include_router(auth.router)
app.include_router(auth_google.router)
app.include_router(profile.router)
app.include_router(dashboard.router)

app.include_router(upload.router)
app.include_router(training.router)
app.include_router(equipment.router)
app.include_router(weightroom.router)

app.include_router(share.router)
app.include_router(metrics.router)
app.include_router(trainer_dashboard.router)
app.include_router(summary.router)
app.include_router(forms.router)
app.include_router(connect.router)

app.include_router(org_financial.router)
app.include_router(org_law.router)
app.include_router(org_oil.router)

app.include_router(assistant.router)

# Pipeline / NLP routers
app.include_router(pipeline_router)
app.include_router(predict_router)
app.include_router(pipeline_ingest_router)
app.include_router(pipeline_async_router)
app.include_router(models_router)


@app.on_event("startup")
def _startup() -> None:
    storage_startup()
    ensure_buckets()
    ensure_indexes()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # keep your current behavior, but return JSON for non-browser callers
    if request.headers.get("accept", "").lower().find("text/html") >= 0:
        return RedirectResponse(url="/")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
