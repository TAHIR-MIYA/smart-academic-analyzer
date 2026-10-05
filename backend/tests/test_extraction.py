import pytest

from app.services.extraction import extract_docx, extract_pdf, extract_text, extract_txt
from app.utils.errors import EmptyDocumentError, MalformedDocumentError

TEXT = "Natural language processing converts raw documents into structured knowledge."


def test_txt_utf8(settings):
    r = extract_txt(TEXT.encode("utf-8"), settings)
    assert r.text == TEXT and r.method == "text:utf-8" and not r.warnings


def test_txt_utf8_bom_removed(settings):
    r = extract_txt(b"\xef\xbb\xbf" + TEXT.encode("utf-8"), settings)
    assert r.text == TEXT


def test_txt_utf16(settings):
    r = extract_txt(TEXT.encode("utf-16"), settings)
    assert r.text == TEXT and r.method == "text:utf-16"


def test_txt_cp1252_fallback_warns(settings):
    r = extract_txt("The café offers résumé workshops daily".encode("cp1252"), settings)
    assert "café" in r.text and r.warnings


def test_txt_windows_line_endings_normalised(settings):
    r = extract_txt(b"first line of text\r\nsecond line of text", settings)
    assert "\r" not in r.text and "\n" in r.text


def test_txt_too_short(settings):
    with pytest.raises(EmptyDocumentError):
        extract_txt(b"hi", settings)


def test_pdf_single_page(settings, make_pdf):
    r = extract_pdf(make_pdf([TEXT]), settings)
    assert "language processing" in r.text and r.page_count == 1 and r.method == "pymupdf"


def test_pdf_multi_page_count(settings, make_pdf):
    r = extract_pdf(make_pdf([TEXT, "Second page content about tokenization and stemming."]), settings)
    assert r.page_count == 2 and "tokenization" in r.text


def test_pdf_page_limit_warns(make_pdf):
    from app.config import Settings

    s = Settings(max_pdf_pages=1)
    r = extract_pdf(make_pdf([TEXT, "Second page content about tokenization."]), s)
    assert r.page_count == 2 and "tokenization" not in r.text and r.warnings


def test_pdf_blank_is_empty_error(settings, make_pdf):
    with pytest.raises(EmptyDocumentError):
        extract_pdf(make_pdf([""]), settings)


def test_pdf_corrupted_is_malformed(settings):
    with pytest.raises(MalformedDocumentError):
        extract_pdf(b"%PDF-1.4\nthis is garbage, not a real pdf body", settings)


def test_docx_paragraphs_and_table_in_order(settings, make_docx):
    r = extract_docx(make_docx([TEXT], table=[["Name", "Marks"], ["Asha", "92"]]), settings)
    assert TEXT in r.text and "Name | Marks" in r.text and "Asha | 92" in r.text


def test_docx_empty_is_empty_error(settings, make_docx):
    with pytest.raises(EmptyDocumentError):
        extract_docx(make_docx([]), settings)


def test_docx_corrupted_is_malformed(settings):
    with pytest.raises(MalformedDocumentError):
        extract_docx(b"PK\x03\x04 not really a docx archive", settings)


def test_dispatch(settings):
    assert extract_text("txt", TEXT.encode(), settings).text == TEXT
