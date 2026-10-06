import pytest

from app.nlp.resources import check_nlp_resources

pytestmark = pytest.mark.skipif(not check_nlp_resources()["ready"], reason="NLP resources not installed")

from app.nlp.pipeline import run_pipeline  # noqa: E402
from app.nlp.readability import analyse_readability, count_syllables  # noqa: E402


@pytest.mark.parametrize("word,expected", [
    ("the", 1), ("make", 1), ("table", 2), ("reading", 2), ("syllable", 3), ("analysis", 4),
    ("natural", 3), ("document", 3), ("agree", 2), ("queue", 1), ("makes", 1), ("wanted", 2),
    ("jumped", 1), ("education", 4), ("houses", 2), ("boxes", 2), ("free", 1), ("requires", 2),
    ("considerable", 5), ("state-of-the-art", 4),
])
def test_syllable_heuristic(word, expected):
    assert count_syllables(word) == expected


def scores(result):
    return {s["name"]: s["value"] for s in result["scores"]}


def test_hand_computed_scores():
    # 12 words, 2 sentences, 12 syllables, 34 letters, 0 complex words
    # FRE  = 206.835 - 1.015*6 - 84.6*1            = 116.145
    # FKGL = 0.39*6 + 11.8*1 - 15.59                = -1.45
    # Fog  = 0.4*(6 + 0)                            = 2.4
    # ARI  = 4.71*(34/12) + 0.5*6 - 21.43           = -5.085
    r = analyse_readability(run_pipeline("The cat sat on the mat. The dog ran in the sun."))
    assert r["counts"] == {"words": 12, "sentences": 2, "syllables": 12, "complex_words": 0, "letters": 34}
    s = scores(r)
    assert s["Flesch Reading Ease"] == pytest.approx(116.145, abs=0.01)
    assert s["Flesch-Kincaid Grade Level"] == pytest.approx(-1.45, abs=0.01)
    assert s["Gunning Fog Index"] == pytest.approx(2.4, abs=0.01)
    assert s["Automated Readability Index"] == pytest.approx(-5.085, abs=0.01)


def test_complex_words_counted():
    r = analyse_readability(run_pipeline("Understanding mathematical relationships requires considerable concentration."))
    assert r["counts"]["words"] == 6 and r["counts"]["complex_words"] == 5
    assert scores(r)["Gunning Fog Index"] == pytest.approx(0.4 * (6 + 100 * 5 / 6), abs=0.01)


def test_harder_text_scores_lower_flesch_and_higher_grade():
    easy = analyse_readability(run_pipeline("The cat sat on the mat. The dog ran in the sun. We like to play. It is fun."))
    hard = analyse_readability(run_pipeline(
        "Comprehensive evaluation methodologies necessitate considerable computational infrastructure. "
        "Interdisciplinary collaboration facilitates theoretical advancement considerably."))
    assert scores(hard)["Flesch Reading Ease"] < scores(easy)["Flesch Reading Ease"]
    assert scores(hard)["Flesch-Kincaid Grade Level"] > scores(easy)["Flesch-Kincaid Grade Level"]


def test_short_text_flagged_unreliable():
    r = analyse_readability(run_pipeline("The cat sat on the mat. The dog ran in the sun."))
    assert r["reliable"] is False and "at least" in r["warning"]


def test_long_text_is_reliable():
    text = " ".join(["The students are studying natural language processing techniques in the laboratory."] * 15)
    r = analyse_readability(run_pipeline(text))
    assert r["reliable"] is True and r["warning"] is None


def test_reading_level_follows_flesch_band():
    r = analyse_readability(run_pipeline("The cat sat on the mat. The dog ran in the sun."))
    assert r["reading_level"].startswith("Very easy")  # FRE 116 >= 90


def test_numbers_and_punctuation_are_not_words():
    r = analyse_readability(run_pipeline("In 2024 the model reached 95 percent accuracy, which was good."))
    assert r["counts"]["words"] == 9  # 2024 and 95 are not counted
