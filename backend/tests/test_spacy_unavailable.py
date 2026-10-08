"""spaCy can be installed yet unloadable (for example blocked by Windows Application Control).
The application must still start, say clearly what is wrong, and keep every non-spaCy feature working."""
import subprocess
import sys

import pytest

from app.nlp import resources
from app.utils.errors import NLPResourceError


@pytest.fixture
def spacy_blocked(monkeypatch):
    """spaCy is present on disk (find_spec succeeds) but importing it fails, as with a blocked DLL."""
    real_find_spec = resources.find_spec
    monkeypatch.setattr(resources, "find_spec", lambda name, *a: object() if name == "spacy" else real_find_spec(name, *a))
    monkeypatch.setitem(sys.modules, "spacy", None)
    resources.spacy_load_problem.cache_clear()
    resources.get_spacy_model.cache_clear()
    yield
    monkeypatch.undo()
    resources.spacy_load_problem.cache_clear()
    resources.get_spacy_model.cache_clear()


def test_the_application_still_imports_and_starts_when_spacy_cannot_load():
    code = "import sys; sys.modules['spacy'] = None; import app.main; print('started')"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert out.returncode == 0 and "started" in out.stdout, out.stderr


def test_the_resource_check_reports_why(spacy_blocked):
    r = resources.check_nlp_resources()
    assert r["ready"] is False
    assert "cannot be loaded" in r["spacy_problem"]
    assert any("cannot be loaded" in m for m in r["missing"])


def test_loading_the_model_raises_a_clear_error_with_the_cause(spacy_blocked):
    with pytest.raises(NLPResourceError) as exc:
        resources.get_spacy_model()
    assert "cannot be loaded on this computer" in exc.value.message
    assert "cause" in exc.value.details


def test_analysis_endpoint_answers_503_not_500(client, spacy_blocked):
    r = client.post("/api/analysis/preview", json={"text": "Natural language processing converts documents into knowledge."})
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "nlp_resources_missing"
    assert "cannot be loaded" in r.json()["error"]["message"]


def test_health_endpoint_and_non_spacy_features_keep_working(client, spacy_blocked):
    health = client.get("/api/health").json()
    assert health["status"] == "ok" and health["nlp_resources"]["ready"] is False
    assert "cannot be loaded" in health["nlp_resources"]["spacy_problem"]
    up = client.post("/api/documents/upload", files={"file": ("n.txt", b"A short text file with enough characters.", "text/plain")})
    assert up.status_code == 201  # uploading and extraction need no spaCy
