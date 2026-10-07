"""Read-only access to the training results written by `python -m app.ml.train`."""
import json
import logging

from app.config import Settings

logger = logging.getLogger(__name__)

EVALUATION_NOTE = (
    "These figures come from separate evaluation sets and describe how the classifier performs in general. "
    "They are not a measure of the accuracy of the prediction made for any single document."
)


def load_metrics(settings: Settings) -> dict | None:
    """The full metrics.json, or None if the model has not been trained (or the file is unreadable)."""
    try:
        return json.loads(settings.metrics_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.info("No usable metrics file at %s (%s)", settings.metrics_path, exc)
        return None


def model_summary(settings: Settings) -> dict:
    metrics = load_metrics(settings)
    if not metrics:
        return {"trained": settings.model_path.exists(), "trained_at": None, "classifier": None, "feature_set": None,
                "evaluations": [], "note": "No training metrics found. Run: python -m app.ml.train"}
    chosen = metrics["selection"]["chosen"]
    evaluations = [
        {"name": name, "description": ev["description"], "n": ev["n"], "accuracy": ev["accuracy"], "macro_f1": ev["macro_f1"]}
        for name, ev in metrics["evaluations"].items() if ev
    ]
    return {"trained": True, "trained_at": metrics["created_at"], "classifier": chosen["classifier"],
            "feature_set": chosen["feature_set"], "evaluations": evaluations, "note": EVALUATION_NOTE}
