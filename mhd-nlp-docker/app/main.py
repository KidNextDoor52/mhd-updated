from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import os
from fastapi.exceptions import HTTPException

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

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # If the user hits an HTML page unauthenticated, send them to login
    if exc.status_code == 401 and "text/html" in request.headers.get("accept", ""):
        return RedirectResponse("/", status_code=307)
    # Otherwise, keep normal JSON errors for API calls
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root(request: Request):
    # Don't rely on session; your auth sets cookies instead
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
def health():
    return {"status": "ok"}
