import pytest

from app.nlp.resources import check_nlp_resources
from app.utils.errors import NLPResourceError

TEXT = (
    "The students are studying natural language processing techniques. "
    "Tokenization splits the text into words, and the models were trained quickly. "
    "Researchers analysed documents containing important keywords."
)

needs_nlp = pytest.mark.skipif(
    not check_nlp_resources()["ready"], reason="NLP resources not installed"
)


def _upload(client, text=TEXT):
    r = client.post("/api/documents/upload", files={"file": ("n.txt", text.encode(), "text/plain")})
    assert r.status_code == 201
    return r.json()["id"]


@needs_nlp
def test_preprocessing_endpoint(client):
    doc_id = _upload(client)
    r = client.get(f"/api/analysis/{doc_id}/preprocessing")
    assert r.status_code == 200
    body = r.json()
    assert body["document_id"] == doc_id and len(body["stages"]) == 5
    assert body["stages"][0]["token_count"] > body["stages"][4]["token_count"]
    assert any(t["term"] == "student" for t in body["top_terms"])
    assert len(body["cleaning"]["operations"]) == 11


@needs_nlp
def test_statistics_endpoint(client):
    doc_id = _upload(client)
    r = client.get(f"/api/analysis/{doc_id}/statistics")
    assert r.status_code == 200
    stats = r.json()["statistics"]
    assert stats["sentences"] == 3 and stats["characters"] == len(TEXT)


@needs_nlp
def test_preview_endpoint(client):
    r = client.post("/api/analysis/preview", json={"text": TEXT})
    assert r.status_code == 200
    body = r.json()
    assert body["preprocessing"]["document_id"] is None
    assert body["statistics"]["words"] > 20


def test_preview_validation(client):
    assert client.post("/api/analysis/preview", json={"text": "short"}).status_code == 422
    assert client.post("/api/analysis/preview", json={}).status_code == 422


def test_unknown_document_404(client):
    r = client.get("/api/analysis/9999/preprocessing")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


@needs_nlp
def test_numbers_only_document_422(client):
    doc_id = _upload(client, "12345 67890 11111 22222 33333 44444")
    r = client.get(f"/api/analysis/{doc_id}/preprocessing")
    assert r.status_code == 422 and r.json()["error"]["code"] == "empty_document"


def test_missing_resources_return_503(client, monkeypatch):
    doc_id = _upload(client)

    def boom(*a, **k):
        raise NLPResourceError("spaCy model missing", details={"fix": "python -m scripts.setup_nlp"})

    monkeypatch.setattr("app.nlp.pipeline.lemmatize_sentences", boom)
    from app.nlp.pipeline import run_pipeline_cached

    run_pipeline_cached.cache_clear()
    r = client.get(f"/api/analysis/{doc_id}/preprocessing")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "nlp_resources_missing"
    assert r.json()["error"]["details"]["fix"] == "python -m scripts.setup_nlp"
    run_pipeline_cached.cache_clear()
