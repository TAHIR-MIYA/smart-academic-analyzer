import math

import pytest

from app.nlp.resources import check_nlp_resources
from app.nlp.vocabulary import mattr

pytestmark = pytest.mark.skipif(not check_nlp_resources()["ready"], reason="NLP resources not installed")

from app.nlp.pipeline import run_pipeline  # noqa: E402
from app.nlp.vocabulary import analyse_vocabulary  # noqa: E402


def by_key(result):
    return {m["key"]: m["value"] for m in result["measures"]}


def test_hand_computed_measures():
    # tokens: the cat sat the cat ran -> N=6, V=4 (the, cat, sat, ran), hapax=2 (sat, ran), dis=2 (the, cat)
    r = analyse_vocabulary(run_pipeline("The cat sat. The cat ran."))
    assert (r["tokens"], r["types"], r["hapax_count"], r["dis_legomena_count"]) == (6, 4, 2, 2)
    m = by_key(r)
    assert m["ttr"] == pytest.approx(4 / 6, abs=1e-4)
    assert m["root_ttr"] == pytest.approx(4 / math.sqrt(6), abs=1e-3)
    assert m["corrected_ttr"] == pytest.approx(4 / math.sqrt(12), abs=1e-3)
    assert m["hapax_ratio"] == pytest.approx(0.5)
    assert m["lexical_density"] == pytest.approx(4 / 6, abs=1e-4)  # 'the' x2 is a stop word
    assert m["mattr"] == pytest.approx(m["ttr"], abs=1e-4)           # text shorter than the window


def test_mattr_hand_computed():
    # windows of 3: [a b a]=2/3, [b a b]=2/3, [a b c]=1  -> mean 0.7778
    assert mattr(["a", "b", "a", "b", "c"], window=3) == pytest.approx((2 / 3 + 2 / 3 + 1) / 3)


def test_mattr_edge_cases():
    assert mattr([], 3) == 0.0
    assert mattr(["x", "x", "x", "x"], 3) == pytest.approx(1 / 3)
    assert mattr(["a", "b", "c", "d"], 10) == 1.0


def test_ttr_falls_with_length_but_mattr_is_stable():
    sentence = "Natural language processing converts raw documents into structured knowledge quickly. "
    short = analyse_vocabulary(run_pipeline(sentence * 6))
    long = analyse_vocabulary(run_pipeline(sentence * 40))
    assert by_key(long)["ttr"] < by_key(short)["ttr"]
    assert by_key(long)["mattr"] == pytest.approx(by_key(short)["mattr"], abs=0.05)


def test_frequency_spectrum_sums_to_types():
    r = analyse_vocabulary(run_pipeline("Alpha beta beta gamma gamma gamma delta delta delta delta epsilon."))
    assert sum(b["count"] for b in r["frequency_spectrum"]) == r["types"]
    assert [b["occurrences"] for b in r["frequency_spectrum"]] == ["1", "2", "3", "4", "5+"]


def test_zipf_table_is_ranked():
    r = analyse_vocabulary(run_pipeline("data data data model model text. data model text analysis."))
    counts = [z["count"] for z in r["zipf"]]
    assert counts == sorted(counts, reverse=True)
    assert r["zipf"][0] == {"rank": 1, "word": "data", "count": 4}


def test_lemma_types_not_more_than_types():
    r = analyse_vocabulary(run_pipeline("Models learn. A model learns. Many models learned patterns."))
    assert r["lemma_types"] < r["types"]


def test_short_text_flagged_unreliable():
    assert analyse_vocabulary(run_pipeline("The cat sat. The cat ran."))["reliable"] is False
