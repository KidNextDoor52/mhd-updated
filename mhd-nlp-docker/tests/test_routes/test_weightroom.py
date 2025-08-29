def test_weightroom_update(client, auth_headers):
    #inital dashboard
    res = client.get("/weightroom/", headers=auth_headers)
    assert res.status_code == 200

    #update with numbers
    res = client.post(
        "/weightroom/update",
        headers=auth_headers,
        data={"bench": "225", "squat": "615", "vertical": "42", "forty_dash": "4.6"},
    )
    assert res.status_code == 303

    #verify update
    res = client.get("/weightroom/", headers=auth_headers)
    assert "225" in res.text
    assert "615" in res.text
    