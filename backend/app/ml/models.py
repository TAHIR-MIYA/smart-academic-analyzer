"""Candidate classifiers. All are linear models that train in seconds on a laptop CPU."""
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from app.ml.features import make_vectorizer

RANDOM_STATE = 42

# Order matters: it is the tie-break order (interpretable + native probabilities first).
CLASSIFIERS = {
    "logistic_regression": lambda: LogisticRegression(C=10.0, max_iter=2000, random_state=RANDOM_STATE),
    # LinearSVC has no probabilities; calibration (sigmoid) adds them.
    "linear_svm": lambda: CalibratedClassifierCV(LinearSVC(C=1.0, random_state=RANDOM_STATE), cv=3),
    "naive_bayes": lambda: MultinomialNB(alpha=0.1),
}


def build_pipeline(classifier: str) -> Pipeline:
    return Pipeline([("tfidf", make_vectorizer()), ("clf", CLASSIFIERS[classifier]())])
