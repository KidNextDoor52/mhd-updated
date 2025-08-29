def test_signup_and_login(client):
    res = client.post("/auth/signup", data={"username": "alice", "password": "wonder"})
    assert res.status_code == 200
    assert "User created" in res.json()["message"]

    res = client.post("/auth/token", data={"username": "alice", "password": "wonder"})
    assert res.status_code == 200
    assert "access_token" in res.json()

def test_profile(client, auth_headers):
    res = client.get("/auth/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["username"] == "testuser"