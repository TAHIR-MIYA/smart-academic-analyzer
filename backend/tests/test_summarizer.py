import pytest

from app.nlp.resources import check_nlp_resources

pytestmark = pytest.mark.skipif(not check_nlp_resources()["ready"], reason="NLP resources not installed")

from app.nlp.pipeline import run_pipeline  # noqa: E402
from app.nlp.summarizer import summarize  # noqa: E402
from app.nlp.tfidf import extract_keywords  # noqa: E402
from app.utils.errors import EmptyDocumentError  # noqa: E402

TEXT = (
    "Natural language processing enables computers to analyse text documents. "          # 0
    "Tokenization splits text into tokens and lemmatization reduces tokens to dictionary forms. "  # 1
    "The weather was pleasant yesterday afternoon. "                                       # 2
    "Natural language processing systems classify documents and extract keywords from text. "     # 3
    "Lunch was served at noon in the cafeteria. "                                          # 4
    "Keyword extraction uses weights to rank important terms in text documents. "          # 5
    "The cafeteria is open daily for students. "                                           # 6
    "Summarization selects the most informative sentences from documents. "                # 7
)
NLP_SENTENCES = {0, 1, 3, 5, 7}


def run(text=TEXT, **kw):
    doc = run_pipeline(text)
    k = extract_keywords(doc, None, 10**6)
    weights = {x["term"]: x["score"] for x in k["keywords"]}
    return summarize(doc, weights, k["idf_mode"], **kw)


def test_picks_on_topic_sentences_not_filler():
    r = run()
    assert {s["index"] for s in r["summary"]} <= NLP_SENTENCES


def test_output_is_in_original_order_and_extractive():
    r = run(num_sentences=3)
    idx = [s["index"] for s in r["summary"]]
    assert idx == sorted(idx) and len(idx) == 3
    doc = run_pipeline(TEXT)
    assert all(s["text"] == doc.sentences[s["index"]] for s in r["summary"])  # nothing is rewritten


def test_default_length_is_about_a_quarter():
    assert run()["sentences_selected"] == 2  # round(0.25 * 8)


def test_num_sentences_respected_and_capped():
    assert run(num_sentences=1)["sentences_selected"] == 1
    r = run(num_sentences=15)
    assert r["sentences_selected"] == r["sentences_eligible"] == 8 and r["note"]


def test_short_fragments_are_not_eligible():
    r = run("Abstract. " + TEXT)
    assert r["sentences_in_document"] == 9 and r["sentences_eligible"] == 8
    frag = next(s for s in r["sentence_scores"] if s["index"] == 0)
    assert frag["score"] == 0 and frag["selected"] is False


def test_redundant_sentences_are_skipped():
    dup = "Natural language processing converts text documents into structured knowledge. "
    text = dup + "Weather is nice today in the city. " + dup + "Tokenization splits text into separate tokens quickly. " \
           "Lemmatization reduces tokens to dictionary forms. Cafeteria food was served at noon today."
    r = run(text, num_sentences=3)
    chosen = [s["text"] for s in r["summary"]]
    assert sum(1 for t in chosen if t.startswith("Natural language processing converts")) == 1


def test_position_bonus_boosts_first_eligible_sentence_only():
    plain = run(position_bonus=0.0)["sentence_scores"]
    boosted = run(position_bonus=0.25)["sentence_scores"]
    assert boosted[0]["score"] == pytest.approx(plain[0]["score"] * 1.25, rel=1e-4)
    assert boosted[1]["score"] == pytest.approx(plain[1]["score"], rel=1e-4)


def test_compression_ratio_between_zero_and_one():
    assert 0 < run()["compression_ratio"] < 1


def test_summary_text_is_joined_selection():
    r = run()
    assert r["summary_text"] == " ".join(s["text"] for s in r["summary"])


def test_deterministic():
    assert run() == run()


def test_document_without_summarisable_sentences_raises():
    doc = run_pipeline("Short one. Tiny two. Brief three.")
    with pytest.raises(EmptyDocumentError):
        summarize(doc, {}, "term_frequency")
