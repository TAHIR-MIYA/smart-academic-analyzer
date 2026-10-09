"""The README's API and configuration tables must match the application, so the documentation cannot drift."""
import re
from pathlib import Path

import pytest

from app.config import Settings
from app.main import app

README = Path(__file__).resolve().parents[2] / "README.md"
pytestmark = pytest.mark.skipif(not README.exists(), reason="README.md is not next to the backend folder")


def _documented_endpoints() -> set[tuple[str, str]]:
    found = set()
    for line in README.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`(GET|POST|DELETE|PUT|PATCH) (/api/[^`]+)`", line)
        if m:
            found.add((m.group(1), m.group(2).split("?")[0]))
    return found


def _real_endpoints() -> set[tuple[str, str]]:
    return {(method.upper(), path) for path, ops in app.openapi()["paths"].items() for method in ops}


def test_every_documented_endpoint_exists():
    assert _documented_endpoints() - _real_endpoints() == set()


def test_every_endpoint_is_documented():
    assert _real_endpoints() - _documented_endpoints() == set()


def test_documented_settings_are_real_and_complete():
    text = README.read_text(encoding="utf-8")
    documented = set(re.findall(r"^\|\s*`([A-Z_]+)`\s*\|", text, flags=re.MULTILINE))
    real = {name.upper() for name in Settings.model_fields} - {"APP_NAME", "APP_VERSION"}
    assert documented == real


def test_every_python_command_in_the_readme_points_at_a_real_module():
    text = README.read_text(encoding="utf-8")
    modules = set(re.findall(r"python -m ([a-z_.]+)", text)) - {"pytest", "venv"}
    root = Path(__file__).resolve().parents[1]
    for module in modules:
        assert (root / (module.replace(".", "/") + ".py")).exists(), module


# ---------------- the written deliverables ----------------
ROOT = README.parent
REPORT_SECTIONS = [
    "Title", "Abstract", "Introduction", "Problem Statement", "Objectives", "Existing System", "Proposed System",
    "System Architecture", "Methodology", "NLP Techniques", "Algorithms", "Dataset", "Implementation",
    "Experimental Results", "Evaluation Metrics", "Screenshots", "Advantages", "Limitations", "Future Scope",
    "Conclusion", "References",
]


def test_report_has_the_21_required_sections_in_order():
    report = ROOT / "PROJECT_REPORT.md"
    if not report.exists():
        pytest.skip("PROJECT_REPORT.md not found")
    headings = re.findall(r"^## (\d+)\. (.+)$", report.read_text(encoding="utf-8"), flags=re.MULTILINE)
    assert [int(n) for n, _ in headings] == list(range(1, 22))
    assert [t.strip() for _, t in headings] == REPORT_SECTIONS


def test_viva_has_at_least_40_numbered_questions_covering_the_required_topics():
    viva = ROOT / "VIVA.md"
    if not viva.exists():
        pytest.skip("VIVA.md not found")
    text = viva.read_text(encoding="utf-8")
    numbers = [int(n) for n in re.findall(r"^\*\*(\d+)\. ", text, flags=re.MULTILINE)]
    assert len(numbers) >= 40 and numbers == list(range(1, len(numbers) + 1))
    required = [r"token[iz]", r"stop words", r"stemming", r"lemmati[sz]", r"tf-idf", r"n-gram", r"named entit|\bner\b",
                r"classif", r"train/test split|train/test", r"precision", r"recall", r"f1", r"cosine", r"summari[sz]",
                r"limitation", r"future"]
    lowered = text.lower()
    missing = [pattern for pattern in required if not re.search(pattern, lowered)]
    assert missing == []


def test_every_viva_answer_is_non_empty():
    viva = ROOT / "VIVA.md"
    if not viva.exists():
        pytest.skip("VIVA.md not found")
    blocks = re.split(r"^\*\*\d+\. .+?\*\*\s*$", viva.read_text(encoding="utf-8"), flags=re.MULTILINE)[1:]
    assert all(len(b.strip().split()) >= 15 for b in blocks[:-1])
