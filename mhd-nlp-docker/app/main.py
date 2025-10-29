from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.exceptions import HTTPException
import os

from app.db.storage import ensure_buckets
from app.routes.pipeline import router as pipeline_router  # ML pipeline API

from app.routes import auth, equipment, weightroom, upload, training, dashboard, auth_google, profile, share
from app.routes import summary, forms, connect
from app.db_init import ensure_indexes

app = FastAPI()
ensure_indexes()

templates = Jinja2Templates(directory="app/templates")
templates.env.auto_reload = True

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "super-secret"),
    same_site="lax"
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

# 👉 add the new ML pipeline router
app.include_router(pipeline_router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.on_event("startup")
async def _start_background_jobs():
    # 1) Make sure object storage is ready (Blob/S3 + mlflow-artifacts container/bucket)
    try:
        ensure_buckets()
    except Exception as e:
        print("Bucket init skipped:", e)

    # 2) Start background scheduler AFTER buckets exist
    #from app.utils.scheduler import start_background_scheduler
    #app.state.scheduler_thread = start_background_scheduler(interval_seconds=24*60*60)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401 and "text/html" in request.headers.get("accept", ""):
        return RedirectResponse("/", status_code=307)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
def health():
    return {"status": "ok"}



#from fastapi import FastAPI, Request
#from fastapi.templating import Jinja2Templates
#from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
#from fastapi.staticfiles import StaticFiles
#from starlette.middleware.sessions import SessionMiddleware
#from fastapi.exceptions import HTTPException
#import os
#from app.db.storage import ensure_buckets
#from app.routes.pipeline import router as pipeline_router
#
#from app.routes import auth, equipment, weightroom, upload, training, dashboard, auth_google, profile, share
#from app.routes import summary, forms, connect
#from app.db_init import ensure_indexes
#
#app = FastAPI()
#ensure_indexes()
#
#templates = Jinja2Templates(directory="app/templates")
#templates.env.auto_reload = True
#
#app.add_middleware(
#    SessionMiddleware,
#    secret_key=os.getenv("SESSION_SECRET_KEY", "super-secret"),
#    same_site="lax"
#)
#
## Routers
#app.include_router(auth.router)
#app.include_router(equipment.router)
#app.include_router(weightroom.router)
#app.include_router(upload.router)
#app.include_router(training.router)
#app.include_router(dashboard.router)
#app.include_router(auth_google.router)
#app.include_router(profile.router)
#app.include_router(share.router)
#app.include_router(summary.router)
#app.include_router(forms.router)
#app.include_router(connect.router)
#
#app.mount("/static", StaticFiles(directory="app/static"), name="static")
#
#@app.on_event("startup")
#async def _start_background_jobs():
#    # Import here so scheduler module loads without pulling sync too early.
#    from app.utils.scheduler import start_background_scheduler
#    # run more frequently in dev if you want: e.g., every 10 minutes = 600
#    app.state.scheduler_thread = start_background_scheduler(interval_seconds=24*60*60)
#
#@app.exception_handler(HTTPException)
#async def http_exception_handler(request: Request, exc: HTTPException):
#    if exc.status_code == 401 and "text/html" in request.headers.get("accept", ""):
#        return RedirectResponse("/", status_code=307)
#    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
#
#@app.get("/", response_class=HTMLResponse, include_in_schema=False)
#def root(request: Request):
#    return templates.TemplateResponse("index.html", {"request": request})
#
#@app.get("/health")
#def health():
#    return {"status": "ok"}
#