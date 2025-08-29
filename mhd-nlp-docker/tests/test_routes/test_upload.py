import io

def test_upload_file(client, auth_headers):
    file_content = io.BytesIO(b"My fake medical file")
    res = client.post(
        "/upload/record",
        headers=auth_headers,
        file={"file": ("test.txt", file_content, "text/plain")}
    )
    assert res.status_code == 303

    #upload file should appear in page
    res = client.get("/upload/", headers=auth_headers)
    assert "test.txt" in res.text
    