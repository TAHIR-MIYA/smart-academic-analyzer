import pytest

from app.nlp.resources import check_nlp_resources

pytestmark = pytest.mark.skipif(
    not check_nlp_resources()["ready"], reason="NLP resources not installed (run python -m scripts.setup_nlp)"
)

from app.nlp.pipeline import run_pipeline  # noqa: E402
from app.nlp.preprocessing import lemmatize_sentences, stem  # noqa: E402
from app.nlp.tokenization import is_word_token, split_sentences, tokenize_words  # noqa: E402
from app.utils.errors import EmptyDocumentError  # noqa: E402

TEXT = (
    "The students are studying natural language processing techniques. "
    "Tokenization splits the text into words, and the models were trained quickly.\n\n"
    "Researchers analysed documents containing important keywords."
)


# ---------- tokenisation ----------
def test_sentence_split_handles_abbreviations():
    sents = split_sentences("Dr. Smith teaches NLP at the university. Students enjoy it.")
    assert len(sents) == 2 and sents[0].startswith("Dr. Smith")


def test_word_tokenize_separates_punctuation():
    toks = tokenize_words("Hello, world!")
    assert toks == ["Hello", ",", "world", "!"]


def test_contractions_split():
    assert tokenize_words("It doesn't work") == ["It", "does", "n't", "work"]


@pytest.mark.parametrize("tok,expected", [
    ("language", True), ("state-of-the-art", True), ("don't", True),
    ("2024", False), ("a", False), (".", False), ("n't", False), ("3.14", False),
])
def test_is_word_token(tok, expected):
    assert is_word_token(tok) is expected


# ---------- lemmatisation / stemming ----------
def test_stem_is_rule_based_and_may_not_be_a_word():
    assert stem("studies") == "studi"
    assert stem("Running") == "run"


def test_lemma_is_pos_aware():
    out = dict(zip(["The", "meeting", "was", "long"], [l for l, _ in lemmatize_sentences([["The", "meeting", "was", "long"]])]))
    assert out["was"] == "be"


def test_lemmatizer_alignment_over_multiple_sentences():
    sents = [["Cats", "run", "."], ["Dogs", "barked", "."]]
    out = lemmatize_sentences(sents)
    assert len(out) == 6
    assert out[0][0] == "cat" and out[4][0] == "bark"


def test_lemmatizer_handles_more_than_one_chunk():
    sents = [["Models", "learn", "."]] * 450  # forces 3 chunks of <= 200 sentences
    out = lemmatize_sentences(sents)
    assert len(out) == 1350 and out[0][0] == "model" and out[-3][0] == "model"


# ---------- full pipeline ----------
def test_stage_counts_are_monotonic():
    rep = run_pipeline(TEXT).preprocessing_report()
    counts = [s["token_count"] for s in rep["stages"]]
    assert counts[0] > counts[1] == counts[2] > counts[3] == counts[4]
    uniques = [s["unique_count"] for s in rep["stages"]]
    assert uniques[4] <= uniques[3] and uniques[2] <= uniques[1]


def test_stopwords_removed_and_lemmas_produced():
    r = run_pipeline(TEXT)
    lemmas = r.content_lemmas
    for stop in ("the", "are", "were", "and", "into"):
        assert stop not in lemmas
    for expected in ("student", "study", "technique", "model", "researcher"):
        assert expected in lemmas


def test_case_folding_merges_types():
    rep = run_pipeline("Language models. language MODELS. The Language.").preprocessing_report()
    assert rep["stages"][2]["unique_count"] < rep["stages"][1]["unique_count"]


def test_stem_vs_lemma_rows_only_where_they_differ():
    rows = run_pipeline(TEXT).preprocessing_report()["stem_vs_lemma"]
    assert rows and all(row["stem"] != row["lemma"] for row in rows)
    studying = next(row for row in rows if row["word"] == "studying")
    assert studying["stem"] == "studi" and studying["lemma"] == "study"


def test_top_terms_ordered_by_frequency():
    rep = run_pipeline("Model model model data data text. Models learn data.").preprocessing_report()
    counts = [t["count"] for t in rep["top_terms"]]
    assert counts == sorted(counts, reverse=True)
    assert rep["top_terms"][0]["term"] == "model"


def test_removed_stopword_rate_between_0_and_1():
    rep = run_pipeline(TEXT).preprocessing_report()
    assert 0 < rep["stopword_removal_rate"] < 1 and rep["removed_stopwords"][0]["term"] == "the"


def test_numbers_only_document_raises():
    with pytest.raises(EmptyDocumentError):
        run_pipeline("12345 67890 11111 22222 33333")


def test_truncation_flag_and_warning():
    r = run_pipeline(TEXT * 20, max_chars=300)
    assert r.truncated and r.preprocessing_report()["warnings"]


def test_cleaning_runs_inside_pipeline():
    r = run_pipeline("Visit https://example.com for \ufb01nancial data about language models today.")
    assert "http" not in r.cleaned_text and "financial" in r.cleaned_text


def test_statistics_values():
    s = run_pipeline(TEXT).statistics()
    assert s["sentences"] == 3 and s["paragraphs"] == 2
    assert s["words"] == 28 or s["words"] > 20
    assert s["characters"] == len(TEXT)
    assert s["unique_words"] <= s["words"]
    assert s["longest_sentence_words"] >= s["avg_sentence_length"]
    assert sum(b["count"] for b in s["sentence_length_distribution"]) == s["sentences"]


def test_pipeline_is_deterministic():
    a, b = run_pipeline(TEXT), run_pipeline(TEXT)
    assert a.content_lemmas == b.content_lemmas


def test_negation_clitic_not_a_content_word():
    lemmas = run_pipeline("The model doesn't overfit and the parser can't fail on long documents.").content_lemmas
    assert "n't" not in lemmas and "overfit" in lemmas
