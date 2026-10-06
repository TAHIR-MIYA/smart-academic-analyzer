import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

from app.ml.evaluate import compute_metrics, mean_max_similarity, save_confusion_matrix_png

LABELS = ["a", "b", "c"]
Y_TRUE = ["a", "a", "b", "b", "c", "c"]
Y_PRED = ["a", "b", "b", "b", "c", "a"]
# Hand-computed confusion matrix (rows = true, cols = predicted):
#        a  b  c
#   a  [ 1, 1, 0 ]
#   b  [ 0, 2, 0 ]
#   c  [ 1, 0, 1 ]


def test_confusion_matrix_orientation():
    assert compute_metrics(Y_TRUE, Y_PRED, LABELS)["confusion_matrix"] == [[1, 1, 0], [0, 2, 0], [1, 0, 1]]


def test_hand_computed_metrics():
    m = compute_metrics(Y_TRUE, Y_PRED, LABELS)
    assert m["accuracy"] == pytest.approx(4 / 6, abs=1e-4)
    pc = m["per_class"]
    assert pc["a"]["precision"] == pytest.approx(0.5) and pc["a"]["recall"] == pytest.approx(0.5)
    assert pc["b"]["precision"] == pytest.approx(2 / 3, abs=1e-4) and pc["b"]["recall"] == 1.0
    assert pc["c"]["precision"] == 1.0 and pc["c"]["recall"] == pytest.approx(0.5)
    assert pc["b"]["f1"] == pytest.approx(0.8)
    assert m["macro_precision"] == pytest.approx((0.5 + 2 / 3 + 1) / 3, abs=1e-4)
    assert m["macro_recall"] == pytest.approx(2 / 3, abs=1e-4)
    assert m["macro_f1"] == pytest.approx((0.5 + 0.8 + 2 / 3) / 3, abs=1e-4)


def test_perfect_predictions():
    m = compute_metrics(Y_TRUE, Y_TRUE, LABELS)
    assert m["accuracy"] == m["macro_f1"] == m["weighted_f1"] == 1.0


def test_class_absent_from_truth_does_not_drag_macro_average():
    m = compute_metrics(["a", "a", "b"], ["a", "a", "b"], ["a", "b", "c"])
    assert m["macro_f1"] == 1.0 and m["per_class"]["c"]["support"] == 0


def test_support_sums_to_n():
    m = compute_metrics(Y_TRUE, Y_PRED, LABELS)
    assert sum(v["support"] for v in m["per_class"].values()) == m["n"] == 6


def test_similarity_identical_vs_unrelated():
    train = ["alpha beta gamma delta", "river mountain forest lake"]
    vec = TfidfVectorizer().fit(train)
    assert mean_max_similarity(vec, train, ["alpha beta gamma delta"]) == pytest.approx(1.0)
    assert mean_max_similarity(vec, train, ["completely different words here"]) == 0.0


def test_confusion_matrix_png_written(tmp_path):
    out = tmp_path / "sub" / "cm.png"
    save_confusion_matrix_png([[1, 1, 0], [0, 2, 0], [1, 0, 1]], LABELS, out, "test")
    assert out.exists() and out.stat().st_size > 1000
