import pytest
from fastapi.testclient import TestClient
import mongomock
from app.main import app
from app import db as real_db

@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    #replace mongodb collections with mongomock in-memory
    mock_client = mongomock.MongoClient()
    mock_db = mock_client["test_db"]

    monkeypatch.setattr(real_db, "db", mock_db)
    monkeypatch.setattr(real_db, "users", mock_db.users)
    monkeypatch.setattr(real_db, "documents", mock_db.documents)
    monkeypatch.setattr(real_db, "medical_history", mock_db.medical_history)
    monkeypatch.setattr(real_db, "equipment", mock_db.equipment)
    monkeypatch.setattr(real_db, "training", mock_db.training)
    monkeypatch.setattr(real_db, "training_flags", mock_db.training_flags)
    monkeypatch.setattr(real_db, "uploads", mock_db.uploads)
    monkeypatch.setattr(real_db, "upload_flags", mock_db.upload_flags)
    monkeypatch.setattr(real_db, "weightroom", mock_db.weightroom)
    
    yield mock_db

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers(client):
    """Signup + login to return an Authorization header"""
    client.post("/auth/signup", data={"username": "testuser", "password": "testpass"})
    res = client.post("/auth/token", data={"username": "testuser", "password": "testpass"})
    token = res.json()["access_token"]
    return{"Authorization": f"Bearer {token}"}