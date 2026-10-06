"""Evaluation helpers: metrics, confusion-matrix image, similarity of evaluation docs to the training set."""
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.metrics.pairwise import cosine_similarity


def compute_metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    """Accuracy, per-class and macro/weighted precision, recall, F1, plus the confusion matrix.

    Rows of the matrix are the TRUE class, columns the PREDICTED class (order = `labels`).
    """
    p, r, f, support = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    present = support > 0  # classes absent from y_true would otherwise drag macro averages to 0
    weights = support / support.sum() if support.sum() else support
    return {
        "n": len(y_true),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_precision": round(float(p[present].mean()), 4),
        "macro_recall": round(float(r[present].mean()), 4),
        "macro_f1": round(float(f[present].mean()), 4),
        "weighted_f1": round(float((f * weights).sum()), 4),
        "per_class": {
            lab: {"precision": round(float(p[i]), 4), "recall": round(float(r[i]), 4),
                  "f1": round(float(f[i]), 4), "support": int(support[i])}
            for i, lab in enumerate(labels)
        },
        "labels": list(labels),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    }


def mean_max_similarity(vectorizer, train_texts: list[str], eval_texts: list[str]) -> float:
    """Average over evaluation documents of the cosine similarity to their nearest training document.

    Values close to 1 mean the evaluation set is almost a copy of the training set, so high
    accuracy on it says little about generalisation.
    """
    train = vectorizer.transform(train_texts)
    ev = vectorizer.transform(eval_texts)
    sims = cosine_similarity(ev, train)
    return round(float(np.mean(sims.max(axis=1))), 4)


def save_confusion_matrix_png(cm: list[list[int]], labels: list[str], path: Path, title: str) -> None:
    import matplotlib

    matplotlib.use("Agg")  # no display needed
    import matplotlib.pyplot as plt

    arr = np.array(cm)
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    im = ax.imshow(arr, cmap="Blues")
    ax.set_xticks(range(len(labels)), [l.replace("_", " ") for l in labels], rotation=35, ha="right")
    ax.set_yticks(range(len(labels)), [l.replace("_", " ") for l in labels])
    ax.set_xlabel("Predicted class")
    ax.set_ylabel("True class")
    ax.set_title(title)
    threshold = arr.max() / 2 if arr.size else 0
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            ax.text(j, i, int(arr[i, j]), ha="center", va="center",
                    color="white" if arr[i, j] > threshold else "black")
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
