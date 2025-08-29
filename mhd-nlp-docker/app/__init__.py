from fastapi import FastAPI 
from .db import get_db
from .routes import auth, equipment, weightroom, upload, training

app = FastAPI(title="MHD WebApp", version="1.0.0")


@app.on_event("startup")
def startup_db_check():
    db = get_db()
    print("Database connection initialized") #check connection at startup

#register our blueprints
app.register_blueprint(auth.bp)
app.register_blueprint(equipment.bp)
app.register_blueprint(weightroom.bp)
app.register_blueprint(upload.bp)
app.register_blueprint(training.bp)

    #root route
@app.get("/")
def home():
    return {"message": "MHD WebApp is running. Go to /login to start."}
