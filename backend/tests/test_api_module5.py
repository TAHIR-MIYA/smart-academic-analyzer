import pytest

from app.config import get_settings
from app.main import app
from app.nlp.resources import check_nlp_resources
from tests.conftest import isolated_settings

needs_nlp = pytest.mark.skipif(not check_nlp_resources()["ready"], reason="NLP resources not installed")

DB_TEXT = (
    "Normalization removes redundancy from relational database tables. "
    "A primary key uniquely identifies each row in a table. "
    "SQL queries join tables using foreign keys. "
    "Indexes speed up queries on large tables. "
    "A transaction groups several database operations into one unit. "
    "Deadlock occurs when two transactions wait for each other. "
    "The ER diagram models entities and relationships in the database. "
    "Students should practise writing SQL queries every week."
)
OTHER = (
    "The football team practised passing drills every morning. "
    "Their coach praised the defenders after the friendly match. "
    "Supporters travelled across the country to watch the final."
)


def _upload(client, text, name="d.txt"):
    r = client.post("/api/documents/upload", files={"file": (name, text.encode(), "text/plain")})
    assert r.status_code == 201
    return r.json()["id"]


@needs_nlp
def test_summary_endpoint(client):
    doc_id = _upload(client, DB_TEXT)
    r = client.get(f"/api/analysis/{doc_id}/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["document_id"] == doc_id and 1 <= body["sentences_selected"] <= 3
    assert body["summary_text"] and len(body["sentence_scores"]) == 8
    r2 = client.get(f"/api/analysis/{doc_id}/summary?sentences=4").json()
    assert r2["sentences_selected"] == 4


def test_summary_sentences_validation(client):
    doc_id = _upload(client, DB_TEXT)
    assert client.get(f"/api/analysis/{doc_id}/summary?sentences=0").status_code == 422
    assert client.get(f"/api/analysis/{doc_id}/summary?sentences=21").status_code == 422


@needs_nlp
def test_readability_and_vocabulary_endpoints(client):
    doc_id = _upload(client, DB_TEXT)
    rd = client.get(f"/api/analysis/{doc_id}/readability").json()
    assert [s["name"] for s in rd["scores"]][0] == "Flesch Reading Ease" and rd["reliable"] is False
    vo = client.get(f"/api/analysis/{doc_id}/vocabulary").json()
    assert vo["tokens"] > 0 and vo["types"] <= vo["tokens"] and {m["key"] for m in vo["measures"]} >= {"ttr", "mattr"}


@needs_nlp
def test_topic_similarity_with_shipped_topic_profiles(client):
    doc_id = _upload(client, DB_TEXT)
    r = client.get(f"/api/analysis/{doc_id}/similarity")
    assert r.status_code == 200
    body = r.json()
    assert body["best_topic"] == "Database Management Systems" and body["topics_compared"] == 10


@needs_nlp
def test_compare_endpoint(client):
    a, b = _upload(client, DB_TEXT, "a.txt"), _upload(client, OTHER, "b.txt")
    r = client.post("/api/analysis/compare", json={"document_a": a, "document_b": b})
    assert r.status_code == 200
    body = r.json()
    assert body["document_a"] == {"id": a, "filename": "a.txt"} and body["document_b"]["filename"] == "b.txt"
    assert body["cosine_similarity"] < 0.2
    same = client.post("/api/analysis/compare", json={"document_a": a, "document_b": a}).json()
    assert same["cosine_similarity"] == pytest.approx(1.0) and same["similar_sentence_pairs"]


def test_compare_errors(client):
    a = _upload(client, DB_TEXT)
    assert client.post("/api/analysis/compare", json={"document_a": a, "document_b": 999}).status_code == 404
    assert client.post("/api/analysis/compare", json={"document_a": a}).status_code == 422


def test_new_endpoints_404_for_unknown_document(client):
    for name in ("summary", "readability", "vocabulary", "similarity"):
        assert client.get(f"/api/analysis/9999/{name}").status_code == 404


@needs_nlp
def test_missing_topics_give_503_but_do_not_break_other_endpoints(client, tmp_path):
    app.dependency_overrides[get_settings] = lambda: isolated_settings(tmp_path, topics_dir=tmp_path / "none")
    doc_id = _upload(client, DB_TEXT)
    r = client.get(f"/api/analysis/{doc_id}/similarity")
    assert r.status_code == 503 and r.json()["error"]["details"]["fix"] == "python -m datasets.build_topics"
    assert client.get(f"/api/analysis/{doc_id}/summary").status_code == 200
    pv = client.post("/api/analysis/preview", json={"text": DB_TEXT}).json()
    assert pv["topic_similarity"] is None and "No topic profile" in pv["topic_similarity_error"]
    assert pv["summary"]["summary_text"]
    other = _upload(client, OTHER)
    assert client.post("/api/analysis/compare", json={"document_a": doc_id, "document_b": other}).status_code == 200


@needs_nlp
def test_preview_contains_every_analysis(client):
    body = client.post("/api/analysis/preview", json={"text": DB_TEXT}).json()
    for key in ("preprocessing", "statistics", "keywords", "ngrams", "entities", "summary", "readability",
                "vocabulary", "topic_similarity"):
        assert body[key], key
    assert body["topic_similarity"]["best_topic"] == "Database Management Systems"
