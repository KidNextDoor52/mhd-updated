from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.exceptions import HTTPException
import os

from app.db.storage import ensure_buckets
from app.routes.pipeline import router as pipeline_router  # ML pipeline API

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
    assistant
)
from app.db_init import ensure_indexes

from app.routes.predict import router as predict_router
from app.routes.pipeline_ingest import router as pipeline_ingest_router
from app.routes.pipeline_async import router as pipeline_async_router
from app.routes.models import router as models_router

from app.monitoring.middleware import APIMetricsMiddleware

from app.db.storage import storage_startup, ensure_buckets

app = FastAPI()
@app.on_event("startup")
def _startup():
    storage_startup()
    ensure_buckets()



templates = Jinja2Templates(directory="app/templates")
templates.env.auto_reload = True

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "super-secret"),
    same_site="lax",
)

# Routers
app.include_router(auth.router)
app.include_router(equipment.router)
app.include_router(weightroom.router)
app.include_router(upload.router)
app.include_router(training.router)
app.include_router(dashboard.router)
app.include_router(auth_google.router)
app.include_router(profile.router)
app.include_router(share.router)
app.include_router(summary.router)
app.include_router(forms.router)
app.include_router(connect.router)
app.include_router(metrics.router)
app.include_router(trainer_dashboard.router)

# ML / pipeline routers
app.include_router(pipeline_router)
app.include_router(predict_router)
app.include_router(pipeline_ingest_router)
app.include_router(pipeline_async_router)
app.include_router(models_router)

app.include_router(org_oil.router)
app.include_router(org_financial.router)
app.include_router(org_law.router)
app.include_router(assistant.router)



app.add_middleware(APIMetricsMiddleware)

static_dir = "app/static"
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    print(f"Static dir missing: {static_dir} (skipping mount)")




@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401 and "text/html" in request.headers.get("accept", ""):
        return RedirectResponse("/", status_code=307)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health():
    return {"status": "ok"}
