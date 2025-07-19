from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from db import documents, athletes, users, medical_history, shared_links, db
from file_processor import process_uploaded_file
from auth import authenticate_user, create_access_token, get_password_hash, get_current_user
from uuid import uuid4, uuid
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

#Dashboard function/filtering
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
    docs_cursor = documents.find(query)
    docs = list(docs_cursor)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "docs": docs
    })

@app.get("/profile", response_class=HTMLResponse)
def profile(request: Request, current_user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("profile.gtml", {
        "request": request,
        "user": current_user
    })

@app.get("/form/create", response_class=HTMLResponse)
def show_form(request: Request, current_user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("create_form.html", {"request": request})

#submitting form function
@app.post("/form/create", response_class=HTMLResponse)
async def submit_form(
    request: Request,
    current_user: dict = Depends(get_current_user),
    name: str = Form(...),
    age: int = Form(...),
    injury_history: str = Form(...),
    status: str = Form(...)
):
    from datetime import datetime
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

#generating share link function
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
        "resource_type": resource_id,
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
        "share_url": f"/sahred/{link_id}",
        "expires_at": expires_at.isoformat()
    }

#Viewing shared link function
@app.get("/shared/{link_id}", response_class=HTMLResponse)
def view_shared_resources(
    link_id: str,
    request: Request,
    password: str = "",
    current_user: dict = Depends(get_current_user)
):
    if not record:
        record = db.shared_links.find_one({"link_id": link_id})
    if not record:
        raise HTTPException(status_code=404, detail="Link not found")
    
    if datetime.utcnow() > datetime.fromisoformat(record["expires_at"]):
        raise HTTPException(status_code=403, detail="Link has Expired")

    if record.get("password"):
        if not password or not bcrypt.checkpw(password.encode(), record["password"].encode()):
            raise HTTPException(status_code=403, detail="Incorrect Password")
            
    #check for role access
    if record["shared_with"] and current_user["username"] != record["shared_with"]:
        raise HTTPException(status_code=403, detail="You are not authorized to access this resource")
    
    #Load the actual data
    if record["resource_type"] == "document":
        doc = db.documents.find_one({"document_id": record["resource_id"]})
        return templates.TemplateResponse("Shared_document.html", {
            "requrest": request,
            "doc": doc
        })
    
    elif record["resource_type"] == "form":
        form = db.medical_history.find_one({"_id": ObjectId(record["resource_id"])})
        return templates.TemplateResponse("shared_form.html", {
            "request": request,
            "form": form
        })
    raise HTTPException(status_code=400, detail="Unsupported resource type")
