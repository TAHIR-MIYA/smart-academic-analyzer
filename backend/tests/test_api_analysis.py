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


# ---------------- Module 3 endpoints ----------------
M3_TEXT = (
    "Natural language processing is a field of artificial intelligence. "
    "Natural language processing helps computers understand text. "
    "Tokenization splits text into tokens. "
    "Lemmatization reduces words to dictionary forms. "
    "Albert Einstein worked at Princeton University in 1933. "
    "Students at Mumbai University study natural language processing."
)


@needs_nlp
def test_keywords_endpoint(client):
    doc_id = _upload(client, M3_TEXT)
    r = client.get(f"/api/analysis/{doc_id}/keywords?top_k=5")
    assert r.status_code == 200
    body = r.json()
    assert len(body["keywords"]) == 5 and body["idf_mode"] == "document_sentences"
    assert body["keywords"][0]["term"] == "language" and body["document_id"] == doc_id


@needs_nlp
def test_ngrams_endpoint(client):
    doc_id = _upload(client, M3_TEXT)
    r = client.get(f"/api/analysis/{doc_id}/ngrams")
    assert r.status_code == 200
    levels = {lv["n"]: lv for lv in r.json()["levels"]}
    assert levels[3]["top"][0]["ngram"] == "natural language processing"


@needs_nlp
def test_entities_endpoint(client):
    doc_id = _upload(client, M3_TEXT)
    r = client.get(f"/api/analysis/{doc_id}/entities")
    assert r.status_code == 200
    labels = {g["label"] for g in r.json()["groups"]}
    assert "PERSON" in labels and "ORG" in labels


@needs_nlp
def test_preview_includes_new_analyses(client):
    body = client.post("/api/analysis/preview", json={"text": M3_TEXT}).json()
    assert body["keywords"]["keywords"] and body["ngrams"]["levels"] and body["entities"]["groups"]


def test_top_k_validation(client):
    doc_id = _upload(client)
    assert client.get(f"/api/analysis/{doc_id}/keywords?top_k=0").status_code == 422
    assert client.get(f"/api/analysis/{doc_id}/ngrams?top_k=1000").status_code == 422


def test_new_endpoints_404_for_unknown_document(client):
    for name in ("keywords", "ngrams", "entities"):
        assert client.get(f"/api/analysis/9999/{name}").status_code == 404


@needs_nlp
def test_reference_corpus_used_when_artifact_exists(client, tmp_path):
    from app.config import Settings, get_settings
    from app.main import app
    from app.nlp.tfidf import ReferenceIdf

    path = tmp_path / "ref.json"
    ReferenceIdf(30, {"text": 20, "language": 5}).save(path)
    app.dependency_overrides[get_settings] = lambda: Settings(reference_idf_path=path)
    doc_id = _upload(client, M3_TEXT)
    body = client.get(f"/api/analysis/{doc_id}/keywords").json()
    assert body["idf_mode"] == "reference_corpus" and body["idf_n_documents"] == 31
