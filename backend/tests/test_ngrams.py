import pytest

from app.nlp.resources import check_nlp_resources

pytestmark = pytest.mark.skipif(not check_nlp_resources()["ready"], reason="NLP resources not installed")

from app.nlp.ngrams import analyse_ngrams  # noqa: E402
from app.nlp.pipeline import run_pipeline  # noqa: E402

TEXT = (
    "Natural language processing is useful. "
    "Natural language processing needs data. "
    "Machine learning improves language models."
)


def level(result, n):
    return next(lv for lv in result["levels"] if lv["n"] == n)


def test_three_levels_present():
    r = analyse_ngrams(run_pipeline(TEXT))
    assert [lv["label"] for lv in r["levels"]] == ["Unigrams", "Bigrams", "Trigrams"]


def test_repeated_trigram_counted():
    top = level(analyse_ngrams(run_pipeline(TEXT)), 3)["top"][0]
    assert top == {"ngram": "natural language processing", "count": 2}


def test_bigram_counts():
    bigrams = {b["ngram"]: b["count"] for b in level(analyse_ngrams(run_pipeline(TEXT)), 2)["top"]}
    assert bigrams["natural language"] == 2 and bigrams["language processing"] == 2


def test_ngrams_do_not_cross_sentence_boundaries():
    r = analyse_ngrams(run_pipeline("Alpha beta gamma. Delta epsilon zeta."), top_k=50)
    bigrams = {b["ngram"] for b in level(r, 2)["top"]}
    assert "gamma delta" not in bigrams and "alpha beta" in bigrams


def test_unigram_total_matches_content_lemmas():
    doc = run_pipeline(TEXT)
    assert level(analyse_ngrams(doc), 1)["total"] == len(doc.content_lemmas)


def test_total_and_distinct_consistent():
    for lv in analyse_ngrams(run_pipeline(TEXT))["levels"]:
        assert lv["distinct"] <= lv["total"]


def test_top_k_respected_and_ties_are_deterministic():
    doc = run_pipeline(TEXT)
    a, b = analyse_ngrams(doc, top_k=3), analyse_ngrams(doc, top_k=3)
    assert a == b and all(len(lv["top"]) <= 3 for lv in a["levels"])


def test_no_stopwords_in_ngrams():
    for lv in analyse_ngrams(run_pipeline(TEXT), top_k=50)["levels"]:
        for item in lv["top"]:
            assert not {"the", "is", "and"} & set(item["ngram"].split())
