import pytest

from app.nlp.resources import check_nlp_resources

pytestmark = pytest.mark.skipif(not check_nlp_resources()["ready"], reason="NLP resources not installed")

from app.nlp.ner import _chunks, extract_entities  # noqa: E402

TEXT = (
    "Albert Einstein worked at Princeton University in 1933. "
    "Google released a new language model in 2018. "
    "Students at Mumbai University study natural language processing."
)


def group(result, label):
    return next((g for g in result["groups"] if g["label"] == label), None)


def test_people_and_organisations_found():
    r = extract_entities(TEXT)
    assert any(e["text"] == "Albert Einstein" for e in group(r, "PERSON")["top"])
    orgs = {e["text"] for e in group(r, "ORG")["top"]}
    assert "Princeton University" in orgs and "Google" in orgs


def test_dates_found():
    dates = {e["text"] for e in group(extract_entities(TEXT), "DATE")["top"]}
    assert {"1933", "2018"} <= dates


def test_totals_consistent():
    r = extract_entities(TEXT)
    assert r["total_entities"] == sum(g["total"] for g in r["groups"])
    assert r["unique_entities"] == sum(g["unique"] for g in r["groups"])
    assert all(g["unique"] <= g["total"] for g in r["groups"])


def test_groups_sorted_by_frequency_and_described():
    r = extract_entities(TEXT)
    totals = [g["total"] for g in r["groups"]]
    assert totals == sorted(totals, reverse=True)
    assert all(g["description"] for g in r["groups"])


def test_aggregation_counts_case_insensitively_and_keeps_common_casing(monkeypatch):
    """Deterministic check of the counting logic using a rule-based recogniser instead of the model."""
    import spacy

    fake = spacy.blank("en")
    ruler = fake.add_pipe("entity_ruler")
    ruler.add_patterns([{"label": "ORG", "pattern": [{"LOWER": "google"}]}])
    monkeypatch.setattr("app.nlp.ner.get_spacy_model", lambda: fake)

    r = extract_entities("Google is big. GOOGLE grows. We use Google daily. Even google tries.")
    org = next(g for g in r["groups"] if g["label"] == "ORG")
    assert org["total"] == 4 and org["unique"] == 1
    assert org["top"] == [{"text": "Google", "count": 4}]  # most common surface form wins


def test_text_without_entities():
    r = extract_entities("the quick brown fox jumps over the lazy dog quietly")
    assert r["total_entities"] == 0 and r["groups"] == []


def test_model_name_reported():
    assert extract_entities(TEXT)["model"] == "en_core_web_sm"


def test_chunking_respects_limit_and_keeps_all_text():
    text = "\n\n".join(f"Paragraph {i} " + "word " * 50 for i in range(40))
    chunks = _chunks(text, max_chars=1000)
    assert len(chunks) > 1 and all(len(c) <= 1100 for c in chunks)
    assert sum(c.count("Paragraph") for c in chunks) == 40


def test_single_huge_paragraph_is_split():
    chunks = _chunks("x" * 2500, max_chars=1000)
    assert [len(c) for c in chunks] == [1000, 1000, 500]
