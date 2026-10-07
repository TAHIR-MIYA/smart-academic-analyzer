import json

import pymupdf
import pytest
from sqlalchemy import select

from app.config import get_settings
from app.db.database import get_db
from app.db.models import AnalysisResult
from app.main import app
from app.nlp.resources import check_nlp_resources
from app.services.export_service import download_name
from tests.conftest import isolated_settings
from tests.test_persistence import NOTICE, SHORT_SENTENCES, TEXT, session, upload

pytestmark = pytest.mark.skipif(not check_nlp_resources()["ready"], reason="NLP resources not installed")


def pdf_text(content: bytes) -> str:
    doc = pymupdf.open(stream=content, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)


def test_download_name_is_ascii_and_safe():
    assert download_name("Report Final (v2).pdf", 3, "json") == "analysis_3_Report_Final_v2.json"
    assert download_name("résumé café.txt", 4, "pdf") == "analysis_4_r_sum_caf.pdf"
    assert download_name("../../etc/passwd", 5, "json") == "analysis_5_passwd.json"
    assert download_name("日本語.txt", 6, "json") == "analysis_6_document.json"
    assert download_name("x" * 200 + ".txt", 7, "json").count("x") == 40


# ----------------------------------------------------------------------------- JSON
def test_json_export(client):
    doc_id = upload(client, name="notes.txt")
    r = client.get(f"/api/export/{doc_id}?format=json")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/json")
    assert r.headers["content-disposition"] == f'attachment; filename="analysis_{doc_id}_notes.json"'
    body = json.loads(r.content)
    assert set(body) == {"export", "analysis", "model_evaluation", "model_evaluation_note"}
    assert body["analysis"]["document"]["filename"] == "notes.txt" and body["model_evaluation"] is None
    assert body["export"]["format_version"] == 1 and "NOT specific" in body["export"]["notes"][1]


def test_export_runs_and_saves_the_analysis_if_missing(client):
    doc_id = upload(client)
    assert client.get(f"/api/documents/{doc_id}").json()["analyzed"] is False
    client.get(f"/api/export/{doc_id}")
    assert client.get(f"/api/documents/{doc_id}").json()["analyzed"] is True


def test_json_export_default_format_is_json(client):
    assert client.get(f"/api/export/{upload(client)}").headers["content-type"].startswith("application/json")


def test_json_keeps_unicode_readable(client):
    doc_id = upload(client, TEXT + " The café served résumé workshops.", name="résumé café.txt")
    r = client.get(f"/api/export/{doc_id}")
    assert r.headers["content-disposition"].isascii()
    assert "résumé café.txt" in r.content.decode("utf-8")  # not \u-escaped


def test_json_includes_model_evaluation_apart_from_the_prediction(trained_client):
    doc_id = upload(trained_client, NOTICE)
    body = json.loads(trained_client.get(f"/api/export/{doc_id}").content)
    assert body["analysis"]["classification"]["label"] == "notice"
    assert body["model_evaluation"]["evaluations"]["test_split"]["n"] > 0
    assert "not a measure" in body["model_evaluation_note"]


def test_refresh_reruns_but_default_uses_the_saved_analysis(client):
    doc_id = upload(client)
    client.get(f"/api/export/{doc_id}")
    db = session()
    row = db.scalar(select(AnalysisResult))
    tampered = dict(row.result)
    tampered["keywords"] = {**tampered["keywords"], "idf_mode": "SAVED-MARKER"}
    row.result = tampered
    db.commit()
    assert json.loads(client.get(f"/api/export/{doc_id}").content)["analysis"]["keywords"]["idf_mode"] == "SAVED-MARKER"
    fresh = json.loads(client.get(f"/api/export/{doc_id}?refresh=true").content)
    assert fresh["analysis"]["keywords"]["idf_mode"] == "document_sentences"


def test_export_errors(client):
    doc_id = upload(client)
    assert client.get("/api/export/9999").status_code == 404
    assert client.get(f"/api/export/{doc_id}?format=docx").status_code == 422


# ----------------------------------------------------------------------------- PDF
def test_pdf_export_without_a_model(client):
    doc_id = upload(client, name="notes.txt")
    r = client.get(f"/api/export/{doc_id}?format=pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == f'attachment; filename="analysis_{doc_id}_notes.pdf"'
    assert r.content.startswith(b"%PDF")
    text = pdf_text(r.content)
    for heading in ("Analysis report", "notes.txt", "Extractive summary", "Text statistics", "Readability",
                    "Keywords (TF-IDF)", "Named entities", "Topic similarity", "Limitations"):
        assert heading in text, heading
    assert "Not available" in text and "no training metrics" in text.replace("\n", " ")


def test_pdf_with_a_model_separates_prediction_from_evaluation(trained_client):
    doc_id = upload(trained_client, NOTICE)
    text = pdf_text(trained_client.get(f"/api/export/{doc_id}?format=pdf").content).replace("\n", " ")
    assert "Predicted class: Notice" in text
    assert "Classifier evaluation (held-out results)" in text and "challenge set" in text
    assert text.index("Predicted class") < text.index("Classifier evaluation")
    assert "not a measure of the accuracy" in text


def test_pdf_escapes_markup_and_keeps_unicode(client):
    text_body = TEXT + " The <b>bold</b> tag & the café served résumé workshops."
    doc_id = upload(client, text_body, name="a<b>&c.txt")
    r = client.get(f"/api/export/{doc_id}?format=pdf")
    assert r.status_code == 200
    text = pdf_text(r.content)
    assert "a<b>&c.txt" in text and "café" in text


def test_pdf_survives_missing_sections(client):
    doc_id = upload(client, SHORT_SENTENCES)
    r = client.get(f"/api/export/{doc_id}?format=pdf")
    assert r.status_code == 200 and "no sentences suitable" in pdf_text(r.content).replace("\n", " ")


def test_pdf_survives_a_very_long_unbroken_word(client):
    doc_id = upload(client, TEXT + " " + "x" * 400 + " end.")
    assert client.get(f"/api/export/{doc_id}?format=pdf").status_code == 200


def test_pdf_has_charts(client):
    doc = pymupdf.open(stream=client.get(f"/api/export/{upload(client)}?format=pdf").content, filetype="pdf")
    assert sum(len(page.get_images()) for page in doc) >= 2  # keyword + topic charts
