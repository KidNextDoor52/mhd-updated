from datetime import datetime, timedelta
from app.db import db

def test_share_document_flow(client, auth_headers):
    # Insert a fake document
    db.documents.insert_one({"document_id": "doc123", "document_type": "medical", "upload_date": "2025-08-28"})

    # Create a share link
    res = client.post(
        "/share",
        headers=auth_headers,
        data={"resource_id": "doc123", "resource_type": "document", "expires_in": 1},  # 1 hour expiry
    )
    assert res.status_code == 200
    share_url = res.json()["share_url"]

    # Access the share link
    res = client.get(share_url, headers=auth_headers)
    assert res.status_code == 200
    assert "medical" in res.text


def test_share_link_expired(client, auth_headers):
    # Insert doc
    db.documents.insert_one({"document_id": "doc456", "document_type": "xray", "upload_date": "2025-08-28"})

    # Create expired link (negative expiry time so it's already expired)
    res = client.post(
        "/share",
        headers=auth_headers,
        data={"resource_id": "doc456", "resource_type": "document", "expires_in": -1},
    )
    share_url = res.json()["share_url"]

    # Try accessing -> should be expired
    res = client.get(share_url, headers=auth_headers)
    assert res.status_code == 403
    assert "Expired" in res.json()["detail"]


def test_share_link_with_password(client, auth_headers):
    # Insert doc
    db.documents.insert_one({"document_id": "doc789", "document_type": "MRI", "upload_date": "2025-08-28"})

    # Create password-protected link
    res = client.post(
        "/share",
        headers=auth_headers,
        data={"resource_id": "doc789", "resource_type": "document", "expires_in": 1, "password": "secretpw"},
    )
    share_url = res.json()["share_url"]

    # Wrong password
    res = client.get(share_url, headers=auth_headers, params={"password": "wrongpw"})
    assert res.status_code == 403
    assert "Incorrect" in res.json()["detail"]

    # Correct password
    res = client.get(share_url, headers=auth_headers, params={"password": "secretpw"})
    assert res.status_code == 200
    assert "MRI" in res.text


def test_share_link_restricted_user(client, auth_headers):
    # Insert doc
    db.documents.insert_one({"document_id": "doc111", "document_type": "EKG", "upload_date": "2025-08-28"})

    # Create another user
    client.post("/auth/signup", data={"username": "bob", "password": "builder"})
    token_res = client.post("/auth/token", data={"username": "bob", "password": "builder"})
    bob_headers = {"Authorization": f"Bearer {token_res.json()['access_token']}"}

    # Share doc with "bob" only
    res = client.post(
        "/share",
        headers=auth_headers,
        data={"resource_id": "doc111", "resource_type": "document", "expires_in": 1, "shared_with": "bob"},
    )
    share_url = res.json()["share_url"]

    # Original user should be blocked
    res = client.get(share_url, headers=auth_headers)
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"].lower()

    # Bob should have access
    res = client.get(share_url, headers=bob_headers)
    assert res.status_code == 200
    assert "EKG" in res.text
