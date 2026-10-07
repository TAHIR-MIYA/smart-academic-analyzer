import pytest
from sqlalchemy import func, select

from app.config import get_settings
from app.db.database import get_db
from app.db.models import AnalysisResult
from app.main import app
from app.nlp.resources import check_nlp_resources
from tests.conftest import isolated_settings

pytestmark = pytest.mark.skipif(not check_nlp_resources()["ready"], reason="NLP resources not installed")

TEXT = (
    "Normalization removes redundancy from relational database tables. "
    "A primary key uniquely identifies each row in a table. "
    "SQL queries join tables using foreign keys. "
    "Indexes speed up queries on large tables. "
    "A transaction groups several database operations into one unit. "
    "Deadlock occurs when two transactions wait for each other. "
    "The ER diagram models entities and relationships in the database. "
    "Students should practise writing SQL queries every week."
)
NOTICE = ("All students are hereby informed that the library will remain closed on Friday. "
          "Students are requested to take note of the above and act accordingly. Principal")
SHORT_SENTENCES = "Cats purr softly. Dogs bark loudly. Birds sing sweetly. Fish swim quietly. Owls hoot often. Bees buzz around."
SECTIONS = ("preprocessing", "statistics", "keywords", "ngrams", "entities", "readability", "vocabulary")


def upload(client, text=TEXT, name="d.txt"):
    r = client.post("/api/documents/upload", files={"file": (name, text.encode("utf-8"), "text/plain")})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def session():
    return next(app.dependency_overrides[get_db]())


def test_run_returns_every_section_and_saves(client):
    doc_id = upload(client)
    r = client.post(f"/api/analysis/{doc_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["document"]["id"] == doc_id and body["schema_version"] == 1
    for key in SECTIONS + ("summary", "topic_similarity"):
        assert body[key], key
    assert body["classification"] is None and "No trained model" in body["classification_error"]
    assert client.get(f"/api/analysis/{doc_id}").json() == body  # what was saved is what is returned


def test_get_before_run_is_404_with_a_hint(client):
    doc_id = upload(client)
    r = client.get(f"/api/analysis/{doc_id}")
    assert r.status_code == 404
    assert r.json()["error"]["details"]["fix"] == f"POST /api/analysis/{doc_id}"


def test_rerun_replaces_instead_of_duplicating(client):
    doc_id = upload(client)
    client.post(f"/api/analysis/{doc_id}")
    client.post(f"/api/analysis/{doc_id}")
    assert session().scalar(select(func.count(AnalysisResult.id))) == 1


def test_document_list_and_detail_show_analyzed_flag(client):
    doc_id = upload(client)
    assert client.get("/api/documents").json()[0]["analyzed"] is False
    assert client.get(f"/api/documents/{doc_id}").json()["analyzed"] is False
    client.post(f"/api/analysis/{doc_id}")
    assert client.get("/api/documents").json()[0]["analyzed"] is True
    assert client.get(f"/api/documents/{doc_id}").json()["analyzed"] is True


def test_deleting_a_document_deletes_its_analysis(client):
    doc_id = upload(client)
    client.post(f"/api/analysis/{doc_id}")
    assert client.delete(f"/api/documents/{doc_id}").status_code == 204
    assert session().scalar(select(func.count(AnalysisResult.id))) == 0


def test_unknown_document_is_404_for_run_and_get(client):
    assert client.post("/api/analysis/9999").status_code == 404
    assert client.get("/api/analysis/9999").status_code == 404


def test_literal_routes_are_not_shadowed_by_the_id_route(client):
    r = client.post("/api/analysis/compare")  # no body: must complain about the BODY, not about a bad id
    assert r.status_code == 422 and r.json()["detail"][0]["loc"][0] == "body"
    r = client.post("/api/analysis/abc")
    assert r.status_code == 422 and r.json()["detail"][0]["loc"] == ["path", "document_id"]
    assert client.post("/api/analysis/preview", json={"text": TEXT}).status_code == 200


def test_optional_sections_fail_softly(client):
    doc_id = upload(client, SHORT_SENTENCES)
    body = client.post(f"/api/analysis/{doc_id}").json()
    assert body["summary"] is None and "no sentences suitable" in body["summary_error"]
    assert body["readability"] and body["keywords"] and body["topic_similarity"]  # everything else still produced


def test_missing_topic_profiles_are_recorded_as_an_error(client, tmp_path):
    app.dependency_overrides[get_settings] = lambda: isolated_settings(tmp_path, topics_dir=tmp_path / "none")
    body = client.post(f"/api/analysis/{upload(client)}").json()
    assert body["topic_similarity"] is None and "topic profile" in body["topic_similarity_error"]
    assert body["summary"]


def test_unanalysable_document_saves_nothing(client):
    doc_id = upload(client, "12345 67890 11111 22222 33333 44444")
    r = client.post(f"/api/analysis/{doc_id}")
    assert r.status_code == 422 and r.json()["error"]["code"] == "empty_document"
    assert client.get(f"/api/analysis/{doc_id}").status_code == 404


def test_classification_is_saved_when_a_model_exists(trained_client):
    doc_id = upload(trained_client, NOTICE)
    body = trained_client.post(f"/api/analysis/{doc_id}").json()
    assert body["classification"]["label"] == "notice" and body["classification_error"] is None


def test_outdated_saved_analysis_gives_409_and_a_rerun_fixes_it(client):
    doc_id = upload(client)
    client.post(f"/api/analysis/{doc_id}")
    db = session()
    row = db.scalar(select(AnalysisResult))
    row.schema_version = 0
    db.commit()
    r = client.get(f"/api/analysis/{doc_id}")
    assert r.status_code == 409 and r.json()["error"]["code"] == "analysis_outdated"
    assert client.post(f"/api/analysis/{doc_id}").status_code == 200
    assert client.get(f"/api/analysis/{doc_id}").status_code == 200
