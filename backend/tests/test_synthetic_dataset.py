import pytest

from datasets.generate_dataset import CLASSES, generate
from app.nlp.resources import check_nlp_resources


def read_all(root):
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8") for p in sorted(root.rglob("*.txt"))}


def test_counts_and_manifest(tmp_path):
    counts = generate(tmp_path, per_class=6, seed=1)
    assert counts == {c: 6 for c in CLASSES}
    rows = (tmp_path / "labels.csv").read_text().strip().splitlines()
    assert rows[0] == "file,label,source" and len(rows) == 1 + 30
    for c in CLASSES:
        assert len(list((tmp_path / c).glob("*.txt"))) == 6


def test_generation_is_deterministic(tmp_path):
    generate(tmp_path / "a", per_class=5, seed=7)
    generate(tmp_path / "b", per_class=5, seed=7)
    assert read_all(tmp_path / "a") == read_all(tmp_path / "b")


def test_different_seeds_differ(tmp_path):
    generate(tmp_path / "a", per_class=5, seed=1)
    generate(tmp_path / "b", per_class=5, seed=2)
    assert read_all(tmp_path / "a") != read_all(tmp_path / "b")


def test_no_duplicate_documents_within_a_class(tmp_path):
    generate(tmp_path, per_class=40, seed=3)
    for c in CLASSES:
        texts = [p.read_text() for p in (tmp_path / c).glob("*.txt")]
        assert len(set(texts)) == len(texts)


def test_regenerating_removes_stale_files(tmp_path):
    generate(tmp_path, per_class=8, seed=1)
    generate(tmp_path, per_class=3, seed=1)
    assert all(len(list((tmp_path / c).glob("*.txt"))) == 3 for c in CLASSES)


def test_documents_have_class_typical_length_ordering(tmp_path):
    generate(tmp_path, per_class=20, seed=4)
    mean = {c: sum(len(p.read_text().split()) for p in (tmp_path / c).glob("*.txt")) / 20 for c in CLASSES}
    assert mean["notice"] < mean["assignment"] < mean["project_report"]


@pytest.mark.skipif(not check_nlp_resources()["ready"], reason="NLP resources not installed")
def test_every_generated_document_passes_the_pipeline(tmp_path):
    from app.nlp.pipeline import run_pipeline

    generate(tmp_path, per_class=5, seed=5)
    for text in read_all(tmp_path).values():
        assert run_pipeline(text).content_lemmas
