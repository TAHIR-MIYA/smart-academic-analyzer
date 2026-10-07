def test_frontend_origin_is_allowed_and_download_name_is_readable(client):
    r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "Content-Disposition" in r.headers["access-control-expose-headers"]


def test_unknown_origin_gets_no_cors_headers(client):
    r = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers
