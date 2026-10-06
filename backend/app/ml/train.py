"""Train and evaluate the document classifier.

    python -m app.ml.train                      # uses datasets/raw (+ challenge / real if present)

Pipeline: documents -> NLP preprocessing -> TF-IDF (1-2 grams) -> linear classifier.

Evaluation protocol (nothing is hand-typed; everything below is written to metrics.json):
  1. Stratified 80/20 split of the dataset (fixed seed).
  2. Model selection by k-fold cross-validation on the TRAINING part only.
  3. The chosen model is fitted on the training part and scored ONCE on:
       - the held-out test split           (same source as training  -> optimistic)
       - the independent challenge set     (hand-written, different style)
       - the real-world set, if provided   (datasets/real/)
"""
import argparse
import json
import logging
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import sklearn
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split

from app.config import BASE_DIR, get_settings
from app.ml import evaluate
from app.ml.dataset import CLASS_NAMES, Sample, dataset_exists, load_folder_dataset
from app.ml.features import FEATURE_SETS, text_for
from app.ml.models import CLASSIFIERS, RANDOM_STATE, build_pipeline
from app.nlp.pipeline import PreprocessedDocument, run_pipeline
from app.nlp.tfidf import build_reference_idf
from app.utils.errors import DatasetError

logger = logging.getLogger(__name__)

TIE_MARGIN = 0.005  # candidates within this CV macro-F1 of the best are treated as tied


def _preprocess(samples: list[Sample], max_chars: int) -> list[PreprocessedDocument]:
    docs = []
    for i, s in enumerate(samples, 1):
        docs.append(run_pipeline(s.text, max_chars))
        if i % 50 == 0 or i == len(samples):
            logger.info("  preprocessed %d/%d documents", i, len(samples))
    return docs


def _evaluate_extra_set(name: str, description: str, root: Path, pipeline, feature_set: str, labels, vectorizer,
                        train_texts: list[str], max_chars: int, artifacts: Path) -> dict | None:
    if not dataset_exists(root):
        logger.info("No documents found for the %s (%s); skipping", name, root)
        return None
    samples = load_folder_dataset(root, require_all_classes=False)
    docs = _preprocess(samples, max_chars)
    texts = [text_for(d, feature_set) for d in docs]
    y_true = [s.label for s in samples]
    y_pred = list(pipeline.predict(texts))
    result = evaluate.compute_metrics(y_true, y_pred, labels)
    result["description"] = description
    result["mean_max_similarity_to_train"] = evaluate.mean_max_similarity(vectorizer, train_texts, texts)
    result["misclassified"] = [
        {"file": s.name, "true": t, "predicted": p}
        for s, t, p in zip(samples, y_true, y_pred) if t != p
    ]
    evaluate.save_confusion_matrix_png(result["confusion_matrix"], labels, artifacts / f"confusion_matrix_{name}.png",
                                       f"Confusion matrix - {name.replace('_', ' ')}")
    return result


def train(data_dir: Path, challenge_dir: Path | None, real_dir: Path | None, artifacts_dir: Path,
          reference_idf_path: Path | None = None, cv_folds: int = 5, test_size: float = 0.2,
          seed: int = RANDOM_STATE, max_chars: int = 500_000) -> dict:
    artifacts_dir = Path(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    labels = sorted(CLASS_NAMES)  # scikit-learn orders classes alphabetically; keep the same order everywhere

    logger.info("Loading dataset from %s", data_dir)
    samples = load_folder_dataset(Path(data_dir), min_per_class=max(cv_folds, 3))
    class_counts = {l: sum(1 for s in samples if s.label == l) for l in labels}
    logger.info("Loaded %d documents: %s", len(samples), class_counts)

    logger.info("Running the NLP pipeline on every document (this is the slow step)")
    docs = _preprocess(samples, max_chars)

    # The reference IDF used for keyword extraction is an unsupervised document-frequency table.
    if reference_idf_path is not None:
        ref = build_reference_idf(docs)
        ref.save(Path(reference_idf_path))
        logger.info("Saved reference IDF (%d documents, %d terms) to %s", ref.n_docs, len(ref.df), reference_idf_path)

    idx = list(range(len(samples)))
    y_all = [s.label for s in samples]
    train_idx, test_idx = train_test_split(idx, test_size=test_size, random_state=seed, stratify=y_all)
    y_train = [y_all[i] for i in train_idx]
    y_test = [y_all[i] for i in test_idx]
    logger.info("Split: %d training / %d test documents", len(train_idx), len(test_idx))

    # ---- model selection on the training split only ----
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=seed)
    candidates = []
    for fs in FEATURE_SETS:
        x_train = [text_for(docs[i], fs) for i in train_idx]
        for clf_name in CLASSIFIERS:
            scores = cross_validate(build_pipeline(clf_name), x_train, y_train, cv=cv,
                                    scoring={"accuracy": "accuracy", "f1": "f1_macro"})
            cand = {"feature_set": fs, "classifier": clf_name,
                    "cv_accuracy_mean": round(float(scores["test_accuracy"].mean()), 4),
                    "cv_macro_f1_mean": round(float(scores["test_f1"].mean()), 4),
                    "cv_macro_f1_std": round(float(scores["test_f1"].std()), 4)}
            candidates.append(cand)
            logger.info("  CV  %-13s + %-19s macro-F1 %.4f (+/- %.4f)", fs, clf_name,
                        cand["cv_macro_f1_mean"], cand["cv_macro_f1_std"])
    best_f1 = max(c["cv_macro_f1_mean"] for c in candidates)
    chosen = next(c for c in candidates if c["cv_macro_f1_mean"] >= best_f1 - TIE_MARGIN)  # canonical order breaks ties
    fs, clf_name = chosen["feature_set"], chosen["classifier"]
    logger.info("Selected: %s + %s", fs, clf_name)

    # ---- fit once on the training split, evaluate ----
    train_texts = [text_for(docs[i], fs) for i in train_idx]
    test_texts = [text_for(docs[i], fs) for i in test_idx]
    pipeline = build_pipeline(clf_name).fit(train_texts, y_train)
    vectorizer = pipeline.named_steps["tfidf"]
    assert list(pipeline.classes_) == labels

    train_acc = float(sum(p == t for p, t in zip(pipeline.predict(train_texts), y_train)) / len(y_train))
    test_pred = list(pipeline.predict(test_texts))
    test_metrics = evaluate.compute_metrics(y_test, test_pred, labels)
    test_metrics["description"] = "Stratified hold-out split of the generated dataset (same source as training)"
    test_metrics["mean_max_similarity_to_train"] = evaluate.mean_max_similarity(vectorizer, train_texts, test_texts)
    test_metrics["misclassified"] = [
        {"file": samples[i].name, "true": y_all[i], "predicted": p}
        for i, p in zip(test_idx, test_pred) if p != y_all[i]
    ]
    evaluate.save_confusion_matrix_png(test_metrics["confusion_matrix"], labels,
                                       artifacts_dir / "confusion_matrix_test_split.png", "Confusion matrix - test split")

    evaluations = {"test_split": test_metrics}
    evaluations["challenge_set"] = (
        _evaluate_extra_set("challenge_set", "Independent hand-written documents in different styles", Path(challenge_dir),
                            pipeline, fs, labels, vectorizer, train_texts, max_chars, artifacts_dir)
        if challenge_dir else None)
    evaluations["real_set"] = (
        _evaluate_extra_set("real_set", "Real documents supplied by the student (datasets/real)", Path(real_dir),
                            pipeline, fs, labels, vectorizer, train_texts, max_chars, artifacts_dir)
        if real_dir else None)

    # ---- explainability: strongest terms per class (logistic regression only) ----
    top_features: dict[str, list[dict]] = {}
    clf = pipeline.named_steps["clf"]
    if hasattr(clf, "coef_"):
        names = vectorizer.get_feature_names_out()
        for row, label in zip(clf.coef_, clf.classes_):
            order = row.argsort()[::-1][:10]
            top_features[label] = [{"term": str(names[j]), "weight": round(float(row[j]), 3)} for j in order]

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    joblib.dump({"pipeline": pipeline, "feature_set": fs, "classifier": clf_name, "labels": labels,
                 "trained_at": now, "n_training_documents": len(train_idx),
                 "sklearn_version": sklearn.__version__}, artifacts_dir / "model.joblib")

    metrics = {
        "created_at": now,
        "random_state": seed,
        "environment": {"python": platform.python_version(), "scikit_learn": sklearn.__version__},
        "dataset": {"path": str(data_dir), "source": "synthetic (template-generated; see datasets/DATASET.md)",
                    "n_documents": len(samples), "class_counts": class_counts,
                    "train_size": len(train_idx), "test_size": len(test_idx), "test_fraction": test_size},
        "features": {"vectorizer": "TF-IDF, word 1-2 grams, min_df=2, sublinear tf", "chosen_feature_set": fs},
        "selection": {"method": f"{cv_folds}-fold stratified cross-validation on the training split only",
                      "criterion": "mean macro-F1",
                      "tie_rule": f"candidates within {TIE_MARGIN} of the best are tied; the first in canonical "
                                  "order (logistic regression, linear SVM, naive Bayes; cleaned text before lemmas) wins",
                      "candidates": candidates, "chosen": chosen},
        "train_accuracy": round(train_acc, 4),
        "evaluations": evaluations,
        "top_features": top_features,
        "notes": [
            "train_accuracy is measured on data the model was fitted to and must not be quoted as performance.",
            "test_split comes from the same generator as the training data, so it is an optimistic estimate.",
            "challenge_set was written by hand in different styles; real_set (if present) is the most honest estimate.",
            "A small evaluation set means every metric has wide uncertainty; one document changes accuracy by 1/n.",
        ],
    }
    (artifacts_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def _summary(m: dict) -> str:
    lines = ["", "=" * 74, "TRAINING SUMMARY", "=" * 74,
             f"Documents: {m['dataset']['n_documents']}  (train {m['dataset']['train_size']} / test {m['dataset']['test_size']})",
             f"Chosen model: {m['selection']['chosen']['feature_set']} + {m['selection']['chosen']['classifier']}",
             f"Training accuracy (NOT a performance figure): {m['train_accuracy']}", ""]
    for name, ev in m["evaluations"].items():
        if not ev:
            lines.append(f"{name}: not evaluated (no documents found)")
            continue
        lines.append(f"{name}  n={ev['n']}  accuracy={ev['accuracy']}  macro-P={ev['macro_precision']}  "
                     f"macro-R={ev['macro_recall']}  macro-F1={ev['macro_f1']}  "
                     f"nearest-train-similarity={ev['mean_max_similarity_to_train']}")
        for item in ev["misclassified"]:
            lines.append(f"    wrong: {item['file']}  true={item['true']}  predicted={item['predicted']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    ap = argparse.ArgumentParser(description="Train the academic document classifier")
    ap.add_argument("--data", default=str(BASE_DIR / "datasets" / "raw"))
    ap.add_argument("--challenge", default=str(BASE_DIR / "datasets" / "challenge"))
    ap.add_argument("--real", default=str(BASE_DIR / "datasets" / "real"))
    ap.add_argument("--artifacts", default=str(settings.model_path.parent))
    ap.add_argument("--cv-folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=RANDOM_STATE)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
    try:
        metrics = train(Path(args.data), Path(args.challenge), Path(args.real), Path(args.artifacts),
                        reference_idf_path=settings.reference_idf_path, cv_folds=args.cv_folds, seed=args.seed,
                        max_chars=settings.max_analysis_chars)
    except DatasetError as exc:
        logger.error("%s", exc)
        logger.error("Generate the dataset first:  python -m datasets.generate_dataset")
        return 1
    print(_summary(metrics))
    print(f"\nArtifacts written to {args.artifacts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
