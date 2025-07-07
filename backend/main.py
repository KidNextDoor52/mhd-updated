from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from db import documents, athletes, users
from file_processor import process_uploaded_file
from auth import authenticate_user, create_access_token, get_password_hash

app = FastAPI()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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
