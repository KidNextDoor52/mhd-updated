def test_training_flow(client, auth_headers):
    # empty training room
    res = client.get("/training/", headers=auth_headers)
    assert res.status_code == 200

    # submit training update
    res = client.post(
        "/training/update",
        headers=auth_headers,
        data={"injury": "knee", "details": "ACL rehab"},

    )
    assert res.status_code == 303

    #training room should now show entry
    res = client.get("/training/", headers=auth_headers)
    assert "knee" in res.text
    