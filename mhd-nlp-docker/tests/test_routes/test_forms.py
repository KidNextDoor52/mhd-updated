def test_create_form(user_and_token, client):
    r = client.post(
        "/form/create",
        headers=user_and_token["headers"],
        data={"name": "John Doe", "age": 25, "injury_history": "ACL tear", "status": "final"}
    )
    assert r.status_code == 200
    assert "Form submitted" in r.text

    # Show in dashboard
    r = client.get("/dashboard", headers=user_and_token["headers"])
    assert "ACL tear" in r.text
