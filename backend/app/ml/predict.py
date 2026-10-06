"""Load the trained model and classify a preprocessed document."""
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib

from app.ml.dataset import DISPLAY_NAMES
from app.ml.features import text_for
from app.nlp.pipeline import PreprocessedDocument
from app.utils.errors import ModelNotTrainedError

logger = logging.getLogger(__name__)
FIX = "python -m app.ml.train"
TOP_EXPLANATION_TERMS = 8

DISCLAIMER = (
    "This is a single prediction for the uploaded document. Accuracy, precision, recall and F1 "
    "are measured on held-out test sets and are reported separately by /api/model/metrics."
)


@dataclass
class ModelBundle:
    pipeline: Any
    feature_set: str
    classifier: str
    labels: list[str]
    trained_at: str
    n_training_documents: int


@lru_cache(maxsize=2)
def _load(path_str: str, mtime_ns: int) -> ModelBundle:
    try:
        raw = joblib.load(path_str)
        return ModelBundle(raw["pipeline"], raw["feature_set"], raw["classifier"], list(raw["labels"]),
                           raw["trained_at"], int(raw["n_training_documents"]))
    except Exception as exc:  # corrupt file, incompatible scikit-learn version, missing keys ...
        logger.exception("Could not load model %s", path_str)
        raise ModelNotTrainedError("The saved model could not be loaded; please retrain it.",
                                   details={"fix": FIX}) from exc


def load_bundle(path: Path) -> ModelBundle:
    try:
        mtime = Path(path).stat().st_mtime_ns
    except OSError as exc:
        raise ModelNotTrainedError("No trained model was found.", details={"fix": FIX}) from exc
    return _load(str(path), mtime)


def _explain(bundle: ModelBundle, text: str, class_index: int) -> list[dict]:
    """Terms that pushed the document towards the predicted class (logistic regression only)."""
    clf = bundle.pipeline.named_steps["clf"]
    if not hasattr(clf, "coef_"):
        return []
    vec = bundle.pipeline.named_steps["tfidf"].transform([text])
    contrib = vec.multiply(clf.coef_[class_index]).tocoo()
    names = bundle.pipeline.named_steps["tfidf"].get_feature_names_out()
    ranked = sorted(zip(contrib.col, contrib.data), key=lambda kv: -kv[1])
    return [{"term": str(names[j]), "contribution": round(float(v), 4)}
            for j, v in ranked[:TOP_EXPLANATION_TERMS] if v > 0]


def classify(doc: PreprocessedDocument, bundle: ModelBundle, min_confidence: float) -> dict:
    text = text_for(doc, bundle.feature_set)
    proba = bundle.pipeline.predict_proba([text])[0]
    classes = list(bundle.pipeline.classes_)
    best = int(proba.argmax())
    label = classes[best]
    confidence = float(proba[best])
    probabilities = sorted(
        ({"label": c, "display_name": DISPLAY_NAMES.get(c, c), "probability": round(float(p), 4)}
         for c, p in zip(classes, proba)), key=lambda d: -d["probability"])
    return {
        "label": label,
        "display_name": DISPLAY_NAMES.get(label, label),
        "confidence": round(confidence, 4),
        "is_confident": confidence >= min_confidence,
        "confidence_threshold": min_confidence,
        "probabilities": probabilities,
        "explanation": _explain(bundle, text, best),
        "model": {"classifier": bundle.classifier, "feature_set": bundle.feature_set,
                  "trained_at": bundle.trained_at, "n_training_documents": bundle.n_training_documents},
        "disclaimer": DISCLAIMER,
    }
