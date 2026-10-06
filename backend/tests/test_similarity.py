import os

import pytest

from app.nlp.resources import check_nlp_resources
from app.utils.errors import NLPResourceError

pytestmark = pytest.mark.skipif(not check_nlp_resources()["ready"], reason="NLP resources not installed")

from app.nlp.pipeline import run_pipeline  # noqa: E402
from app.nlp.similarity import compare_documents, load_topics, topic_similarity  # noqa: E402

DB = ("Database tables store rows and columns. SQL queries join tables using a primary key. "
      "Normalization reduces redundancy in relational databases and indexes speed up queries.")
THERMO = ("Heat engines convert heat into work. Entropy measures the disorder of a system. "
          "The first law states that energy is conserved in every thermodynamic cycle of a gas.")


@pytest.fixture
def topics_dir(tmp_path):
    d = tmp_path / "topics"
    d.mkdir()
    (d / "databases.txt").write_text(DB)
    (d / "thermodynamics.txt").write_text(THERMO)
    return d


def test_topic_names_come_from_file_names(topics_dir):
    (topics_dir / "machine_learning.txt").write_text("Models learn patterns from training data using algorithms.")
    assert [t.name for t in load_topics(topics_dir)] == ["Databases", "Machine Learning", "Thermodynamics"]


def test_best_topic_found(topics_dir):
    doc = run_pipeline("Students write SQL queries to join database tables. A primary key identifies every row in a table.")
    r = topic_similarity(doc, load_topics(topics_dir))
    assert r["best_topic"] == "Databases" and r["is_weak_match"] is False
    assert r["similarities"][0]["topic"] == "Databases"
    assert any(t["term"] in {"table", "query", "sql", "database"} for t in r["matched_terms"])


def test_similarities_sorted_and_bounded(topics_dir):
    r = topic_similarity(run_pipeline(DB), load_topics(topics_dir))
    sims = [s["similarity"] for s in r["similarities"]]
    assert sims == sorted(sims, reverse=True) and all(0 <= s <= 1 for s in sims) and len(sims) == 2


def test_unrelated_document_is_a_weak_match(topics_dir):
    doc = run_pipeline("We baked bread with flour and butter and served fresh jam with warm tea at breakfast.")
    r = topic_similarity(doc, load_topics(topics_dir))
    assert r["is_weak_match"] is True and r["best_topic"] is None and r["note"]


def test_missing_or_empty_topics_folder_raises_with_fix(tmp_path):
    for path in (tmp_path / "nope", tmp_path):
        with pytest.raises(NLPResourceError) as exc:
            load_topics(path)
        assert exc.value.details["fix"] == "python -m datasets.build_topics"


def test_edited_topic_file_is_reloaded(topics_dir):
    before = [t.lemma_text for t in load_topics(topics_dir)]
    f = topics_dir / "databases.txt"
    f.write_text("Completely different vocabulary about rivers and mountains and forests.")
    st = f.stat()
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    after = [t.lemma_text for t in load_topics(topics_dir)]
    assert before != after


# ---------------- document <-> document ----------------
A = ("Tokenization splits written documents into separate tokens before lemmatization. "
     "Stop words are removed because they carry little topical meaning for classification. "
     "Cosine similarity compares the term vectors of two documents.")
UNRELATED = ("The football team practised passing drills every morning. "
             "Their coach praised the defenders after the friendly match. "
             "Supporters travelled across the country to watch the final.")


def test_identical_documents():
    a = run_pipeline(A)
    r = compare_documents(a, a, [])
    assert r["cosine_similarity"] == pytest.approx(1.0) and r["vocabulary_overlap_jaccard"] == 1.0
    assert r["interpretation"] == "Near-identical content"


def test_unrelated_documents():
    r = compare_documents(run_pipeline(A), run_pipeline(UNRELATED), [])
    assert r["cosine_similarity"] < 0.2 and r["interpretation"] == "Mostly unrelated"
    assert r["similar_sentence_pairs"] == []


def test_similarity_is_symmetric():
    a, b = run_pipeline(A), run_pipeline(A.replace("Stop words", "Common words") + " " + UNRELATED)
    assert compare_documents(a, b, [])["cosine_similarity"] == pytest.approx(compare_documents(b, a, [])["cosine_similarity"])


def test_copied_sentence_is_found_with_correct_indexes():
    b_text = UNRELATED + " Tokenization splits written documents into separate tokens before lemmatization."
    r = compare_documents(run_pipeline(A), run_pipeline(b_text), [])
    pair = r["similar_sentence_pairs"][0]
    assert pair["similarity"] > 0.95 and pair["index_a"] == 0 and pair["index_b"] == 3
    assert pair["sentence_a"].startswith("Tokenization splits")


def test_each_sentence_used_in_at_most_one_pair():
    r = compare_documents(run_pipeline(A), run_pipeline(A), [])
    a_idx = [p["index_a"] for p in r["similar_sentence_pairs"]]
    b_idx = [p["index_b"] for p in r["similar_sentence_pairs"]]
    assert len(set(a_idx)) == len(a_idx) and len(set(b_idx)) == len(b_idx)


def test_shared_terms_reported():
    r = compare_documents(run_pipeline(A), run_pipeline(A + " " + UNRELATED), [])
    assert r["shared_terms"] and r["shared_terms"][0]["weight"] > 0


def test_topics_change_the_idf_corpus_but_not_identity(topics_dir):
    a = run_pipeline(A)
    with_topics = compare_documents(a, a, load_topics(topics_dir))
    assert with_topics["cosine_similarity"] == pytest.approx(1.0) and "2 topic profiles" in with_topics["method"]
