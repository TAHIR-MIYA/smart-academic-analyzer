import json

import joblib
import pytest

from app.ml.dataset import CLASS_NAMES
from app.ml.train import train
from app.utils.errors import DatasetError


def test_artifacts_written(trained_artifacts):
    out = trained_artifacts["artifacts"]
    for name in ("model.joblib", "metrics.json", "confusion_matrix_test_split.png", "confusion_matrix_challenge_set.png"):
        assert (out / name).exists(), name
    assert trained_artifacts["reference"].exists()


def test_metrics_internally_consistent(trained_artifacts):
    ev = trained_artifacts["metrics"]["evaluations"]["test_split"]
    cm = ev["confusion_matrix"]
    total = sum(sum(row) for row in cm)
    assert total == ev["n"] == trained_artifacts["metrics"]["dataset"]["test_size"]
    assert ev["accuracy"] == pytest.approx(sum(cm[i][i] for i in range(len(cm))) / total, abs=1e-4)
    assert sum(v["support"] for v in ev["per_class"].values()) == ev["n"]
    assert 0.0 <= ev["macro_f1"] <= 1.0


def test_split_is_stratified_and_disjoint_in_size(trained_artifacts):
    d = trained_artifacts["metrics"]["dataset"]
    assert d["n_documents"] == 50 and d["train_size"] + d["test_size"] == 50
    assert d["test_size"] == 10  # 20 % of 50
    assert all(v == 10 for v in d["class_counts"].values())


def test_model_selection_recorded_honestly(trained_artifacts):
    sel = trained_artifacts["metrics"]["selection"]
    assert len(sel["candidates"]) == 6
    assert sel["chosen"] in sel["candidates"]
    best = max(c["cv_macro_f1_mean"] for c in sel["candidates"])
    assert sel["chosen"]["cv_macro_f1_mean"] >= best - 0.005
    assert "training split only" in sel["method"]


def test_train_accuracy_is_kept_separate_and_labelled(trained_artifacts):
    m = trained_artifacts["metrics"]
    assert "train_accuracy" in m and any("train_accuracy" in n for n in m["notes"])


def test_challenge_evaluated_and_real_set_absent(trained_artifacts):
    ev = trained_artifacts["metrics"]["evaluations"]
    assert ev["challenge_set"]["n"] == 20 and ev["real_set"] is None
    assert 0 <= ev["challenge_set"]["mean_max_similarity_to_train"] <= 1


def test_saved_bundle_loads_and_predicts_known_classes(trained_artifacts):
    bundle = joblib.load(trained_artifacts["model"])
    assert bundle["labels"] == sorted(CLASS_NAMES) and bundle["n_training_documents"] == 40
    text = (trained_artifacts["root"] / "raw" / "notice" / "doc_001.txt").read_text()
    assert bundle["pipeline"].predict([text])[0] in CLASS_NAMES


def test_reference_idf_covers_whole_dataset(trained_artifacts):
    ref = json.loads(trained_artifacts["reference"].read_text())
    assert ref["n_docs"] == 50 and len(ref["df"]) > 50


def test_logistic_regression_exposes_top_features(trained_artifacts):
    top = trained_artifacts["metrics"]["top_features"]
    if trained_artifacts["metrics"]["selection"]["chosen"]["classifier"] == "logistic_regression":
        assert set(top) == set(CLASS_NAMES) and all(len(v) == 10 for v in top.values())


def test_training_is_deterministic(trained_artifacts, tmp_path):
    again = train(trained_artifacts["root"] / "raw", trained_artifacts["root"] / "challenge", None,
                  tmp_path / "out", cv_folds=3, seed=42)
    first = trained_artifacts["metrics"]
    assert again["evaluations"]["test_split"] == first["evaluations"]["test_split"]
    assert again["selection"]["candidates"] == first["selection"]["candidates"]


def test_missing_dataset_raises_clear_error(tmp_path):
    with pytest.raises(DatasetError, match="not found"):
        train(tmp_path / "nope", None, None, tmp_path / "out")
