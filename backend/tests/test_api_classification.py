import pytest

from app.main import app
from app.config import get_settings
from tests.conftest import isolated_settings

NOTICE = ("All students are hereby informed that the library will remain closed on Friday. "
          "Students are requested to take note of the above and act accordingly. Principal")


def _upload(client, text=NOTICE):
    r = client.post("/api/documents/upload", files={"file": ("n.txt", text.encode(), "text/plain")})
    assert r.status_code == 201
    return r.json()["id"]


# ---------- no model trained ----------
def test_classification_503_when_model_missing(client):
    doc_id = _upload(client)
    r = client.get(f"/api/analysis/{doc_id}/classification")
    assert r.status_code == 503
    body = r.json()["error"]
    assert body["code"] == "model_not_trained" and body["details"]["fix"] == "python -m app.ml.train"


def test_metrics_503_when_missing(client):
    assert client.get("/api/model/metrics").status_code == 503


def test_preview_survives_missing_model(client):
    r = client.post("/api/analysis/preview", json={"text": NOTICE})
    assert r.status_code == 200
    body = r.json()
    assert body["classification"] is None and "No trained model" in body["classification_error"]
    assert body["keywords"]["keywords"]  # the other analyses still work


def test_health_reports_untrained_model(client):
    model = client.get("/api/health").json()["model"]
    assert model["trained"] is False and model["fix"] == "python -m app.ml.train"


def test_corrupt_model_file_is_handled(client, tmp_path):
    bad = tmp_path / "bad.joblib"
    bad.write_bytes(b"this is not a joblib file")
    app.dependency_overrides[get_settings] = lambda: isolated_settings(tmp_path, model_path=bad)
    doc_id = _upload(client)
    r = client.get(f"/api/analysis/{doc_id}/classification")
    assert r.status_code == 503 and "could not be loaded" in r.json()["error"]["message"]


# ---------- trained model ----------
def test_classification_endpoint(trained_client):
    doc_id = _upload(trained_client)
    r = trained_client.get(f"/api/analysis/{doc_id}/classification")
    assert r.status_code == 200
    body = r.json()
    assert body["document_id"] == doc_id and body["label"] in {p["label"] for p in body["probabilities"]}
    probs = [p["probability"] for p in body["probabilities"]]
    assert probs == sorted(probs, reverse=True) and sum(probs) == pytest.approx(1.0, abs=1e-3)
    assert body["confidence"] == probs[0] and len(body["probabilities"]) == 5
    assert "metrics" in body["disclaimer"]


def test_obvious_notice_is_classified_as_notice(trained_client):
    doc_id = _upload(trained_client)
    assert trained_client.get(f"/api/analysis/{doc_id}/classification").json()["label"] == "notice"


def test_explanation_terms_are_present_and_positive(trained_client):
    doc_id = _upload(trained_client)
    body = trained_client.get(f"/api/analysis/{doc_id}/classification").json()
    if body["model"]["classifier"] == "logistic_regression":
        assert body["explanation"] and all(t["contribution"] > 0 for t in body["explanation"])


def test_confidence_threshold_flag(trained_client, trained_artifacts, tmp_path):
    app.dependency_overrides[get_settings] = lambda: isolated_settings(
        tmp_path, model_path=trained_artifacts["model"], classification_min_confidence=0.9999)
    doc_id = _upload(trained_client)
    body = trained_client.get(f"/api/analysis/{doc_id}/classification").json()
    assert body["is_confident"] is False and body["confidence_threshold"] == 0.9999


def test_metrics_endpoint_serves_saved_file(trained_client, trained_artifacts):
    body = trained_client.get("/api/model/metrics").json()
    assert body["evaluations"]["test_split"]["n"] == trained_artifacts["metrics"]["evaluations"]["test_split"]["n"]
    assert "train_accuracy" in body and "selection" in body


def test_preview_includes_classification(trained_client):
    body = trained_client.post("/api/analysis/preview", json={"text": NOTICE}).json()
    assert body["classification"]["label"] == "notice" and body["classification_error"] is None


def test_health_reports_trained_model(trained_client):
    assert trained_client.get("/api/health").json()["model"]["trained"] is True


def test_classification_404_for_unknown_document(trained_client):
    assert trained_client.get("/api/analysis/9999/classification").status_code == 404
