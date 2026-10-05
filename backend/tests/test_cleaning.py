from app.nlp.cleaning import clean_text


def ops(result):
    return {o["name"]: o["count"] for o in result.operations}


def test_ligatures_normalised():
    r = clean_text("The \ufb01nancial \ufb02ow improved.")
    assert r.text == "The financial flow improved."
    assert ops(r)["Unicode normalisation"] == 2


def test_hyphenated_line_break_rejoined():
    r = clean_text("Information retrieval needs informa-\ntion about documents.")
    assert "information about documents" in r.text
    assert ops(r)["Hyphenated line breaks"] == 1


def test_real_hyphens_preserved():
    r = clean_text("This is a well-known and state-of-the-art method.")
    assert "well-known" in r.text and "state-of-the-art" in r.text


def test_hyphen_before_capital_not_joined():
    r = clean_text("Pre-\nProcessing is the first step in the pipeline.")
    assert "Pre-" in r.text


def test_soft_hyphen_removed():
    r = clean_text("lemma\u00adtisation is useful for normalising vocabulary.")
    assert "lemmatisation" in r.text


def test_urls_and_emails_removed():
    r = clean_text("See https://example.com/paper and www.site.org or mail a.b@uni.edu today for details.")
    assert "http" not in r.text and "www" not in r.text and "@" not in r.text
    assert ops(r)["URLs"] == 2 and ops(r)["E-mail addresses"] == 1


def test_page_number_lines_removed():
    text = "First paragraph about processing text.\n\n12\n\nPage 3 of 10\n\nSecond paragraph about tokens."
    r = clean_text(text)
    assert "12" not in r.text and "Page 3" not in r.text
    assert ops(r)["Page numbers"] == 2


def test_numbers_inside_sentences_kept():
    r = clean_text("The model reached 95 percent accuracy on 12 documents.")
    assert "95" in r.text and "12" in r.text


def test_repeated_header_removed():
    header = "Department of Computer Engineering"
    text = "\n".join([header, "Content of page one is here.", header, "Content of page two is here.", header, "Content of page three."])
    r = clean_text(text)
    assert header not in r.text
    assert ops(r)["Repeated headers/footers"] == 3


def test_short_repeated_lines_are_kept():
    text = "Answer\nOne.\nAnswer\nTwo.\nAnswer\nThree."
    assert clean_text(text).text.count("Answer") == 3


def test_soft_wrapped_lines_joined():
    r = clean_text("Natural language\nprocessing is useful.")
    assert r.text == "Natural language processing is useful."


def test_heading_line_break_preserved():
    r = clean_text("Introduction\nNatural language processing is useful.")
    assert "Introduction\nNatural" in r.text


def test_sentence_end_line_break_preserved():
    r = clean_text("First sentence ends here.\nsecond starts lower case.")
    assert "here.\nsecond" in r.text


def test_curly_quotes_and_dashes():
    r = clean_text("\u201cHello\u201d \u2013 it\u2019s fine")
    assert '"Hello"' in r.text and "it's" in r.text


def test_whitespace_collapsed():
    r = clean_text("too    many     spaces\n\n\n\n\nnew paragraph")
    assert "  " not in r.text and "\n\n\n" not in r.text


def test_idempotent():
    messy = "\ufb01rst   line\nof text.\n\n3\n\nSee http://a.com now. Informa-\ntion here."
    once = clean_text(messy).text
    assert clean_text(once).text == once


def test_lengths_reported():
    r = clean_text("Some   text  here.")
    assert r.original_length == 18 and r.cleaned_length == len(r.text)


def test_empty_input():
    assert clean_text("").text == ""
