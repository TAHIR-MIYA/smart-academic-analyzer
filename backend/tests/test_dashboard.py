import pytest

from app.nlp.resources import check_nlp_resources
from app.services import model_service
from tests.conftest import isolated_settings
from tests.test_persistence import NOTICE, TEXT, upload

pytestmark = pytest.mark.skipif(not check_nlp_resources()["ready"], reason="NLP resources not installed")


def test_empty_dashboard(client):
    body = client.get("/api/dashboard/summary").json()
    assert body["total_documents"] == 0 and body["analyzed_documents"] == 0 and body["total_words"] == 0
    assert body["by_file_type"] == {} and body["class_distribution"] == [] and body["recent_documents"] == []
    assert body["model"]["trained"] is False and "python -m app.ml.train" in body["model"]["note"]


def test_counts_types_words_and_recent_order(client):
    a = upload(client, TEXT, "a.txt")
    b = upload(client, NOTICE, "b.txt")
    client.post(f"/api/analysis/{a}")
    body = client.get("/api/dashboard/summary").json()
    assert body["total_documents"] == 2 and body["analyzed_documents"] == 1
    assert body["by_file_type"] == {"txt": 2}
    assert body["total_words"] == sum(d["word_count"] for d in client.get("/api/documents").json())
    assert [d["id"] for d in body["recent_documents"]] == [b, a]  # newest first
    assert {d["id"]: d["analyzed"] for d in body["recent_documents"]} == {a: True, b: False}


def test_recent_documents_capped_at_five(client):
    for i in range(7):
        upload(client, TEXT, f"d{i}.txt")
    assert len(client.get("/api/dashboard/summary").json()["recent_documents"]) == 5


def test_class_distribution_comes_from_saved_predictions(trained_client, trained_artifacts):
    notice_text = (trained_artifacts["root"] / "raw" / "notice" / "doc_001.txt").read_text()
    for name in ("n1.txt", "n2.txt"):
        trained_client.post(f"/api/analysis/{upload(trained_client, notice_text, name)}")
    body = trained_client.get("/api/dashboard/summary").json()
    assert body["class_distribution"][0] == {"label": "notice", "display_name": "Notice", "count": 2}
    assert sum(c["count"] for c in body["class_distribution"]) == body["analyzed_documents"]
    assert isinstance(body["uncertain_predictions"], int)


def test_unclassified_documents_are_not_counted_in_the_distribution(client):
    client.post(f"/api/analysis/{upload(client)}")  # no model -> classification is null
    body = client.get("/api/dashboard/summary").json()
    assert body["analyzed_documents"] == 1 and body["class_distribution"] == []


def test_model_block_labels_the_evaluation_sets(trained_client):
    model = trained_client.get("/api/dashboard/summary").json()["model"]
    assert model["trained"] is True and model["classifier"]
    names = {e["name"] for e in model["evaluations"]}
    assert {"test_split", "challenge_set"} <= names and "not a measure" in model["note"]


def test_dashboard_drops_deleted_documents(client):
    doc_id = upload(client)
    client.post(f"/api/analysis/{doc_id}")
    client.delete(f"/api/documents/{doc_id}")
    body = client.get("/api/dashboard/summary").json()
    assert body["total_documents"] == 0 and body["analyzed_documents"] == 0


def test_model_service_handles_missing_and_corrupt_metrics(tmp_path):
    s = isolated_settings(tmp_path)
    assert model_service.load_metrics(s) is None
    (tmp_path / "bad.json").write_text("{nope")
    assert model_service.load_metrics(isolated_settings(tmp_path, metrics_path=tmp_path / "bad.json")) is None
    assert model_service.model_summary(s)["trained"] is False
