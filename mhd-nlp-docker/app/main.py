from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.routes import auth, equipment, weightroom, upload, training, dashboard

app = FastAPI()

# Configure Jinja2
templates = Jinja2Templates(directory="app/templates")
templates.env.auto_reload = True

# Register routers
app.include_router(auth.router)
app.include_router(equipment.router)
app.include_router(weightroom.router)
app.include_router(upload.router)
app.include_router(training.router)
app.include_router(dashboard.router)

# Serve static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
def health():
    return {"status": "ok"}
