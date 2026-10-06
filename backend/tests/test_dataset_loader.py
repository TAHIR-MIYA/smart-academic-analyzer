import pytest

from app.ml.dataset import CLASS_NAMES, load_folder_dataset
from app.utils.errors import DatasetError

TEXT = "Natural language processing converts raw documents into structured knowledge."


def build(tmp_path, per_class=2):
    for c in CLASS_NAMES:
        (tmp_path / c).mkdir()
        for i in range(per_class):
            (tmp_path / c / f"d{i}.txt").write_text(f"{TEXT} {c} number {i}", encoding="utf-8")


def test_loads_all_classes(tmp_path):
    build(tmp_path)
    samples = load_folder_dataset(tmp_path)
    assert len(samples) == 10 and {s.label for s in samples} == set(CLASS_NAMES)
    assert samples[0].name.startswith("assignment/")


def test_missing_folder_raises(tmp_path):
    with pytest.raises(DatasetError):
        load_folder_dataset(tmp_path / "nope")


def test_too_few_documents_per_class_raises(tmp_path):
    build(tmp_path, per_class=1)
    with pytest.raises(DatasetError, match="at least 3"):
        load_folder_dataset(tmp_path, min_per_class=3)


def test_partial_dataset_allowed_for_evaluation_sets(tmp_path):
    (tmp_path / "notice").mkdir()
    (tmp_path / "notice" / "a.txt").write_text(TEXT)
    samples = load_folder_dataset(tmp_path, require_all_classes=False)
    assert [s.label for s in samples] == ["notice"]


def test_unknown_folders_and_other_extensions_ignored(tmp_path):
    build(tmp_path)
    (tmp_path / "misc").mkdir()
    (tmp_path / "misc" / "x.txt").write_text(TEXT)
    (tmp_path / "notice" / "image.png").write_bytes(b"\x89PNG")
    assert len(load_folder_dataset(tmp_path)) == 10


def test_pdf_and_docx_are_supported(tmp_path, make_pdf, make_docx):
    build(tmp_path)
    (tmp_path / "notice" / "real.pdf").write_bytes(make_pdf([TEXT]))
    (tmp_path / "assignment" / "real.docx").write_bytes(make_docx([TEXT]))
    assert len(load_folder_dataset(tmp_path)) == 12


def test_empty_and_corrupt_files_are_skipped(tmp_path):
    build(tmp_path)
    (tmp_path / "notice" / "empty.txt").write_text("")
    (tmp_path / "notice" / "bad.pdf").write_bytes(b"%PDF-1.4 garbage garbage garbage")
    assert len(load_folder_dataset(tmp_path)) == 10
