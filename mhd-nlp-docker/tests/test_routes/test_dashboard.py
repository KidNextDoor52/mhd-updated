def test_dashboard_empty(client, auth_headers):
    res = client.get("/dashboard/", headers=auth_headers)
    assert res.status_code == 200
    assert "No documents" in res.text or "docs" in res.text