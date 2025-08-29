# app/main.py
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
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

@app.get("/")
def root():
    return {"message": "MHD WebApp running. Go to /auth/signup or /auth/token"}
