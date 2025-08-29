def test_profile_me(user_and_token, client):
    r = client.get("/auth/me", headers=user_and_token["headers"])
    assert r.status_code == 200
    assert r.json()["username"] == "alice"
