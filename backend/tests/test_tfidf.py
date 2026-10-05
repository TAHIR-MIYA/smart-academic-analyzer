import math

import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

from app.nlp.resources import check_nlp_resources

pytestmark = pytest.mark.skipif(not check_nlp_resources()["ready"], reason="NLP resources not installed")

from app.nlp.pipeline import run_pipeline  # noqa: E402
from app.nlp.tfidf import (  # noqa: E402
    ReferenceIdf, build_reference_idf, extract_keywords, load_reference_idf, smooth_idf,
)

TEXT = (
    "Tokenization splits text into tokens. "
    "Lemmatization reduces words to dictionary forms. "
    "The classifier uses text features. "
    "Evaluation reports precision and recall for the classifier. "
    "The classifier needs training text. "
    "Cosine similarity compares two text vectors. "
)


def test_smooth_idf_matches_scikit_learn():
    docs = ["alpha beta gamma", "alpha beta", "alpha", "delta alpha"]
    vec = TfidfVectorizer(smooth_idf=True, norm=None).fit(docs)
    n = len(docs)
    df = {"alpha": 4, "beta": 2, "gamma": 1, "delta": 1}
    for term, idx in vec.vocabulary_.items():
        assert math.isclose(vec.idf_[idx], smooth_idf(n, df[term]), rel_tol=1e-9)


def test_sentence_mode_ranks_distinctive_terms_above_ubiquitous_ones():
    k = extract_keywords(run_pipeline(TEXT))
    assert k["idf_mode"] == "document_sentences" and k["idf_n_documents"] >= 5
    by_term = {x["term"]: x for x in k["keywords"]}
    # 'text' appears in 4 of 6 sentences -> lower idf than a term from a single sentence
    assert by_term["text"]["idf"] < by_term["tokenization"]["idf"]
    # 'classifier' appears 3 times, so frequency still beats rarity here
    assert k["keywords"][0]["term"] in {"classifier", "text"}


def test_scores_sorted_and_relative_score_normalised():
    k = extract_keywords(run_pipeline(TEXT))
    scores = [x["score"] for x in k["keywords"]]
    assert scores == sorted(scores, reverse=True)
    assert k["keywords"][0]["relative_score"] == 1.0
    assert all(0 < x["relative_score"] <= 1 for x in k["keywords"])


def test_score_equals_tf_times_idf():
    k = extract_keywords(run_pipeline(TEXT))
    for x in k["keywords"]:
        assert math.isclose(x["score"], x["tf"] * x["idf"], rel_tol=1e-3, abs_tol=1e-5)


def test_top_k_respected():
    assert len(extract_keywords(run_pipeline(TEXT), top_k=3)["keywords"]) == 3


def test_pos_filter_excludes_verbs():
    k = extract_keywords(run_pipeline(TEXT))
    assert k["pos_filter"] == ["NOUN", "PROPN", "ADJ"]
    terms = {x["term"] for x in k["keywords"]}
    assert "split" not in terms and "reduce" not in terms


def test_short_document_falls_back_to_term_frequency():
    k = extract_keywords(run_pipeline("Neural networks learn representations. Neural models need data."))
    assert k["idf_mode"] == "term_frequency"
    assert all(x["idf"] == 1.0 for x in k["keywords"])
    assert k["keywords"][0]["term"] == "neural"


def test_deterministic():
    a = extract_keywords(run_pipeline(TEXT))
    b = extract_keywords(run_pipeline(TEXT))
    assert a == b


def test_reference_corpus_mode_changes_idf(tmp_path):
    refs = [
        run_pipeline("The classifier uses text features for training. Text data is everywhere."),
        run_pipeline("Text mining uses text features. The classifier needs labelled data."),
        run_pipeline("Databases store tables and indexes. Queries read tables."),
    ]
    ref = build_reference_idf(refs)
    assert ref.n_docs == 3 and ref.df["text"] == 2 and ref.df["table"] == 1

    k = extract_keywords(run_pipeline(TEXT), reference=ref)
    assert k["idf_mode"] == "reference_corpus" and k["idf_n_documents"] == 4
    by_term = {x["term"]: x for x in k["keywords"]}
    # 'text' is in 2 reference docs (+ this one); 'tokenization' in none (+ this one)
    assert math.isclose(by_term["text"]["idf"], round(smooth_idf(4, 3), 4))
    assert math.isclose(by_term["tokenization"]["idf"], round(smooth_idf(4, 1), 4))


def test_reference_roundtrip(tmp_path):
    path = tmp_path / "ref.json"
    ReferenceIdf(5, {"text": 3, "model": 2}).save(path)
    loaded = load_reference_idf(path)
    assert loaded.n_docs == 5 and loaded.df == {"text": 3, "model": 2}


def test_missing_or_corrupt_reference_is_ignored(tmp_path):
    assert load_reference_idf(tmp_path / "missing.json") is None
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert load_reference_idf(bad) is None
