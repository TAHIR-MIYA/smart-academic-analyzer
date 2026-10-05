TEXT = b"Natural language processing converts raw documents into structured knowledge."


def _upload(client, name, data, mime="application/octet-stream"):
    return client.post("/api/documents/upload", files={"file": (name, data, mime)})


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["database"] == "ok" and "nlp_resources" in body


def test_upload_txt_and_fetch(client):
    r = _upload(client, "notes.txt", TEXT, "text/plain")
    assert r.status_code == 201
    doc = r.json()
    assert doc["original_filename"] == "notes.txt" and doc["file_type"] == "txt"
    assert doc["word_count"] == 9 and doc["extracted_text"].startswith("Natural")

    got = client.get(f"/api/documents/{doc['id']}")
    assert got.status_code == 200 and got.json()["id"] == doc["id"]


def test_upload_pdf(client, make_pdf):
    r = _upload(client, "paper.pdf", make_pdf([TEXT.decode()]), "application/pdf")
    assert r.status_code == 201 and r.json()["page_count"] == 1


def test_upload_docx(client, make_docx):
    r = _upload(client, "essay.docx", make_docx([TEXT.decode()]))
    assert r.status_code == 201 and r.json()["file_type"] == "docx"


def test_list_hides_text(client):
    _upload(client, "a.txt", TEXT)
    _upload(client, "b.txt", TEXT)
    r = client.get("/api/documents")
    assert r.status_code == 200 and len(r.json()) == 2
    assert "extracted_text" not in r.json()[0]


def test_delete_then_404(client):
    doc_id = _upload(client, "a.txt", TEXT).json()["id"]
    assert client.delete(f"/api/documents/{doc_id}").status_code == 204
    r = client.get(f"/api/documents/{doc_id}")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


def test_unsupported_type_415(client):
    r = _upload(client, "image.png", b"\x89PNG....")
    assert r.status_code == 415 and r.json()["error"]["code"] == "unsupported_file_type"


def test_empty_file_400(client):
    r = _upload(client, "a.txt", b"")
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_file"


def test_too_large_413(tiny_limit_client):
    r = _upload(tiny_limit_client, "big.txt", b"word " * 1000)
    assert r.status_code == 413 and r.json()["error"]["code"] == "file_too_large"


def test_blank_pdf_422(client, make_pdf):
    r = _upload(client, "scan.pdf", make_pdf([""]))
    assert r.status_code == 422 and r.json()["error"]["code"] == "empty_document"


def test_corrupted_pdf_422(client):
    r = _upload(client, "bad.pdf", b"%PDF-1.4 garbage garbage garbage")
    assert r.status_code == 422 and r.json()["error"]["code"] == "malformed_document"


def test_missing_file_field_422(client):
    assert client.post("/api/documents/upload").status_code == 422
