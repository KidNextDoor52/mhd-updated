from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from .db import documents, athletes, users, medical_history, shared_links, db
from .file_processor import process_uploaded_file
from .auth import authenticate_user, create_access_token, get_password_hash, get_current_user
from uuid import uuid4
from datetime import datetime, timedelta
import bcrypt
from bson.objectid import ObjectId

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
templates = Jinja2Templates(directory="frontend")

@app.get("/", response_class=HTMLResponse)
def root():
    with open("frontend/index.html", "r") as f:
        return f.read()

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    file_data = await file.read()
    metadata = process_uploaded_file(file_data)

    athletes.update_one(
        {"athlete_id": metadata["athlete_id"]},
        {"$setOnInsert": {"first_name": "John", "last_name": "Doe"}},
        upsert=True
    )

    documents.insert_one(metadata)
    return {"message": "File uploaded successfully", "metadata": metadata}

@app.post("/signup")
def signup(form_data: OAuth2PasswordRequestForm = Depends()):
    hashed_password = get_password_hash(form_data.password)
    user = {"username": form_data.username, "password": hashed_password}
    users.insert_one(user)
    return {"message": "User created"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token({"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    tag: str = "",
    date: str = "",
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if tag:
        query["tags"] = {"$in": [tag.lower()]}
    if date:
        query["upload_date"] = {"$regex": f"^{date}"}
    docs = list(documents.find(query))
    forms = list(medical_history.find({"athlete_id": current_user["username"]}))
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "docs": docs,
        "forms": forms
    })

@app.get("/profile", response_class=HTMLResponse)
def profile(request: Request, current_user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": current_user
    })

@app.get("/form/create", response_class=HTMLResponse)
def show_form(request: Request, current_user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("create_form.html", {"request": request})

@app.post("/form/create", response_class=HTMLResponse)
async def submit_form(
    request: Request,
    current_user: dict = Depends(get_current_user),
    name: str = Form(...),
    age: int = Form(...),
    injury_history: str = Form(...),
    status: str = Form(...)
):
    form_data = {
        "athlete_id": current_user["username"],
        "name": name,
        "age": age,
        "injury_history": injury_history,
        "status": status,
        "submitted_at": datetime.utcnow().isoformat()
    }
    medical_history.insert_one(form_data)
    return templates.TemplateResponse("create_form.html", {
        "request": request,
        "message": "Form submitted successfully!"
    })

@app.post("/share")
def share_resource(
    resource_id: str = Form(...),
    resource_type: str = Form(...),
    expires_in: int = Form(...),
    password: str = Form(None),
    shared_with: str = Form(None),
    current_user: dict = Depends(get_current_user)
):
    expires_at = datetime.utcnow() + timedelta(hours=expires_in)
    link_id = str(uuid4())

    share_record = {
        "link_id": link_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "shared_by": current_user["username"],
        "shared_with": shared_with,
        "expires_at": expires_at.isoformat(),
    }

    if password:
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        share_record["password"] = hashed_pw.decode()

    db.shared_links.insert_one(share_record)

    return {
        "share_url": f"/shared/{link_id}",
        "expires_at": expires_at.isoformat()
    }

@app.get("/shared/{link_id}", response_class=HTMLResponse)
def view_shared_resources(
    link_id: str,
    request: Request,
    password: str = "",
    current_user: dict = Depends(get_current_user)
):  
    record = db.shared_links.find_one({"link_id": link_id})
    if not record:
        raise HTTPException(status_code=404, detail="Link not found")
    
    if datetime.utcnow() > datetime.fromisoformat(record["expires_at"]):
        raise HTTPException(status_code=403, detail="Link has Expired")

    if record.get("password"):
        if not password or not bcrypt.checkpw(password.encode(), record["password"].encode()):
            raise HTTPException(status_code=403, detail="Incorrect Password")
            
    if record["shared_with"] and current_user["username"] != record["shared_with"]:
        raise HTTPException(status_code=403, detail="You are not authorized to access this resource")
    
    if record["resource_type"] == "document":
        doc = db.documents.find_one({"document_id": record["resource_id"]})
        return templates.TemplateResponse("Shared_document.html", {
            "request": request,
            "doc": doc
        })
    
    elif record["resource_type"] == "form":
        form = db.medical_history.find_one({"_id": ObjectId(record["resource_id"])})
        return templates.TemplateResponse("shared_form.html", {
            "request": request,
            "form": form
        })

    raise HTTPException(status_code=400, detail="Unsupported resource type")

@app.get("/equipment/onboard", response_class=HTMLResponse)
def equipment_onboarding(request: Request, current_user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("equipment_onboard.html", {
        "request": request,
        "user": current_user
    })

@app.post("/equipment/onboard")
async def save_equipment_form(
    request: Request,
    current_user: dict = Depends(get_current_user),
    cleats_type: str = Form(...),
    cleats_size: str = Form(...),
    helmet_type: str = Form(...),
    helmet_size: str = Form(...),
    shoulder_pad_size: str = Form(...),
    mouthpiece: str = Form(...),
    gloves: str = Form(...),
    contacts: bool = Form(False),
    measurement: str = Form(...)
):
    equipment = {
        "username": current_user["username"],
        "cleats": {"type": cleats_type, "size": cleats_size},
        "helmet": {"type": helmet_type, "size": helmet_size},
        "shoulder_pads": {"size": shoulder_pad_size},
        "mouthpiece": "Battle Oxygen",
        "gloves": gloves,
        "contacts": contacts,
        "measurement": measurement,
        "first_time": False
    }
    db.user_equipment.replace_one(
        {"username": current_user["username"]},
        equipment,
        upsert=True
    )
    return RedirectResponse("/equipment", status_code=303)

@app.get("/equipment", response_class=HTMLResponse)
def view_equipment_room(request: Request, current_user: dict = Depends(get_current_user)):
    record = db.user_equipment.find_one({"username": current_user["username"]})

    if not record:
        return RedirectResponse("/equiptment/onboard", status_code=303)
    
    return templates.TemplateRespnse("equipment_room.html", {
        "request": request,
        "equipment": record
    })

@app.get("/equipment/edit/{item}", response_class=HTMLResponse)
def edit_gear_item(item: str, request: Request, current_user: dict = Depends(get_current_user)):
    gear = db.user_equipment 