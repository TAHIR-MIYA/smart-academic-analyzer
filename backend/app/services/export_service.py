"""Export a document's analysis as JSON or as a PDF report (ReportLab + Matplotlib charts)."""
import io
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from sqlalchemy.orm import Session

from app.config import Settings
from app.services import analysis_store, model_service

logger = logging.getLogger(__name__)

EXPORT_FORMAT_VERSION = 1
LIMITATIONS = [
    "Named entities come from a model trained on news and web text; labels for technical terms can be wrong.",
    "Readability formulas are designed for continuous prose and use an estimated syllable count.",
    "The extractive summary only selects existing sentences; its quality has not been scored automatically.",
    "Classification is limited to five document types and can be wrong; check the stated confidence.",
    "Topic similarity compares wording with the supplied topic profiles, not meaning.",
]


# ----------------------------------------------------------------------------- payload
def build_export_payload(db: Session, document_id: int, settings: Settings, refresh: bool = False) -> dict:
    analysis = analysis_store.get_or_run(db, document_id, settings, refresh)
    return {
        "export": {
            "format_version": EXPORT_FORMAT_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "generator": f"{settings.app_name} v{settings.app_version}",
            "notes": [
                "'analysis.classification' is a single prediction for this document.",
                "'model_evaluation' reports held-out evaluation of the classifier and is NOT specific to this document.",
            ],
        },
        "analysis": analysis,
        "model_evaluation": model_service.load_metrics(settings),
        "model_evaluation_note": model_service.EVALUATION_NOTE,
    }


def export_json(payload: dict) -> bytes:
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def download_name(original: str, document_id: int, extension: str) -> str:
    """ASCII-only file name, safe inside a Content-Disposition header."""
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(original).stem).strip("_")[:40] or "document"
    return f"analysis_{document_id}_{stem}.{extension}"


# ----------------------------------------------------------------------------- fonts
_FONTS: dict[str, str] | None = None


def _fonts() -> dict[str, str]:
    """Register DejaVu Sans (shipped with Matplotlib) for broad Unicode coverage; fall back to Helvetica."""
    global _FONTS
    if _FONTS is not None:
        return _FONTS
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    try:
        import matplotlib

        folder = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
        pdfmetrics.registerFont(TTFont("DejaVu", str(folder / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(folder / "DejaVuSans-Bold.ttf")))
        _FONTS = {"regular": "DejaVu", "bold": "DejaVu-Bold"}
    except Exception:  # noqa: BLE001 - any failure just means a plainer font
        logger.warning("DejaVu fonts unavailable; using Helvetica (non-Latin characters may not render)")
        _FONTS = {"regular": "Helvetica", "bold": "Helvetica-Bold"}
    return _FONTS


# ----------------------------------------------------------------------------- charts
def _bar_chart_png(labels: list[str], values: list[float], title: str, xlabel: str, color: str = "#2563eb") -> bytes:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = max(len(labels), 1)
    fig, ax = plt.subplots(figsize=(6.6, 0.38 * n + 1.3))
    ax.barh(range(n), values[::-1] if values else [0], color=color)
    ax.set_yticks(range(n), labels[::-1] if labels else [""])
    ax.set_xlabel(xlabel)
    ax.set_title(title, fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    return buf.getvalue()


# ----------------------------------------------------------------------------- PDF
def _p(text) -> str:
    return escape(str(text))


def build_pdf(payload: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    f = _fonts()
    navy = colors.HexColor("#1e3a8a")
    body = ParagraphStyle("body", fontName=f["regular"], fontSize=9.5, leading=13.5)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=10.5, textColor=colors.HexColor("#444444"))
    cell = ParagraphStyle("cell", parent=body, fontSize=8.2, leading=10.5, wordWrap="CJK")
    cell_head = ParagraphStyle("cell_head", parent=cell, fontName=f["bold"], textColor=colors.white)
    h1 = ParagraphStyle("h1", parent=body, fontName=f["bold"], fontSize=19, leading=23, textColor=navy, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=body, fontName=f["bold"], fontSize=12.5, leading=16, textColor=navy,
                        spaceBefore=12, spaceAfter=4, keepWithNext=True)
    note = ParagraphStyle("note", parent=small, backColor=colors.HexColor("#fff7ed"), borderPadding=5, spaceBefore=7, spaceAfter=6)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=10, bulletIndent=0)

    a = payload["analysis"]
    doc_info = a["document"]
    story: list = []
    width = A4[0] - 36 * mm

    def table(rows: list[list], widths: list[float] | None = None) -> Table:
        data = [[Paragraph(_p(c), cell_head) for c in rows[0]]]
        data += [[Paragraph(_p(c), cell) for c in r] for r in rows[1:]]
        t = Table(data, colWidths=[w * width for w in widths] if widths else None, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), navy),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c7cde0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6fb")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    def chart(labels, values, title, xlabel, color="#2563eb"):
        png = _bar_chart_png(labels, values, title, xlabel, color)
        from PIL import Image as PILImage

        w, h = PILImage.open(io.BytesIO(png)).size
        return Image(io.BytesIO(png), width=width * 0.74, height=width * 0.74 * h / w)

    def unavailable(message):
        return Paragraph(f"Not available: {_p(message)}", note)

    # ---- title and document
    story += [Paragraph("Smart Academic Document Analyzer", h1),
              Paragraph(f"Analysis report &nbsp;|&nbsp; generated {_p(a['generated_at'])} &nbsp;|&nbsp; "
                        f"{_p(payload['export']['generator'])}", small), Spacer(1, 6)]
    story.append(Paragraph("Document", h2))
    size_kb = doc_info["size_bytes"] / 1024
    story.append(table([["Property", "Value"],
                        ["File name", doc_info["filename"]], ["Type", doc_info["file_type"].upper()],
                        ["Size", f"{size_kb:.1f} KB"],
                        ["Pages", doc_info["page_count"] if doc_info["page_count"] is not None else "n/a"],
                        ["Characters / words", f"{doc_info['char_count']:,} / {doc_info['word_count']:,}"],
                        ["Uploaded", doc_info["uploaded_at"]]], [0.3, 0.7]))
    for w in doc_info.get("extraction_warnings") or []:
        story.append(Paragraph(f"Extraction warning: {_p(w)}", note))

    # ---- classification
    story.append(Paragraph("Classification (prediction for this document)", h2))
    c = a.get("classification")
    if c:
        verdict = "confident" if c["is_confident"] else f"UNCERTAIN (below the {c['confidence_threshold']:.2f} threshold)"
        story.append(Paragraph(f"Predicted class: <b>{_p(c['display_name'])}</b> &nbsp;|&nbsp; confidence "
                               f"{c['confidence']:.1%} ({verdict})", body))
        story.append(Spacer(1, 4))
        story.append(chart([p["display_name"] for p in c["probabilities"]], [p["probability"] for p in c["probabilities"]],
                           "Class probabilities", "probability", "#0d9488"))
        if c["explanation"]:
            story.append(Paragraph("Terms that pushed the prediction: " +
                                   ", ".join(f"{_p(t['term'])} ({t['contribution']:.3f})" for t in c["explanation"]), small))
        story.append(Paragraph(_p(c["disclaimer"]), note))
    else:
        story.append(unavailable(a.get("classification_error") or "no classifier"))

    # ---- summary
    story.append(Paragraph("Extractive summary", h2))
    s = a.get("summary")
    if s:
        story.append(Paragraph(f"{s['sentences_selected']} of {s['sentences_in_document']} sentences selected "
                               f"({s['compression_ratio']:.0%} of the words). Sentences are copied from the document.", small))
        for item in s["summary"]:
            story.append(Paragraph(_p(item["text"]), bullet, bulletText="•"))
    else:
        story.append(unavailable(a.get("summary_error") or "summary"))

    # ---- statistics
    st = a["statistics"]
    story.append(Paragraph("Text statistics", h2))
    story.append(table([["Measure", "Value"],
                        ["Characters (with / without spaces)", f"{st['characters']:,} / {st['characters_no_spaces']:,}"],
                        ["Words incl. numbers (unique)", f"{st['words']:,} ({st['unique_words']:,})"],
                        ["Sentences / paragraphs", f"{st['sentences']:,} / {st['paragraphs']:,}"],
                        ["Average word length", f"{st['avg_word_length']} letters"],
                        ["Average sentence length", f"{st['avg_sentence_length']} words"],
                        ["Longest sentence", f"{st['longest_sentence_words']} words"],
                        ["Estimated reading time", f"{st['reading_time_minutes']} min"]], [0.5, 0.5]))

    # ---- readability
    rd = a["readability"]
    story.append(Paragraph("Readability", h2))
    story.append(table([["Index", "Score", "Interpretation"]] +
                       [[x["name"], x["value"], x["interpretation"]] for x in rd["scores"]], [0.38, 0.14, 0.48]))
    if rd.get("warning"):
        story.append(Paragraph(_p(rd["warning"]), note))
    story.append(Paragraph(_p(rd["note"]), small))

    # ---- vocabulary
    vo = a["vocabulary"]
    story.append(Paragraph("Vocabulary diversity", h2))
    story.append(table([["Measure", "Value"], ["Alphabetic words of 2+ letters / distinct", f"{vo['tokens']:,} / {vo['types']:,}"],
                        ["Distinct lemmas", f"{vo['lemma_types']:,}"],
                        ["Words used once (hapax)", f"{vo['hapax_count']:,}"]] +
                       [[m["name"], m["value"]] for m in vo["measures"]], [0.6, 0.4]))
    if vo.get("warning"):
        story.append(Paragraph(_p(vo["warning"]), note))

    # ---- keywords
    kw = a["keywords"]
    top = kw["keywords"][:10]
    head = [Paragraph("Keywords (TF-IDF)", h2), Paragraph(_p(kw["idf_description"]), small)]
    if top:
        head.append(chart([k["term"] for k in top], [k["score"] for k in top], "Top keywords by TF-IDF score", "tf x idf"))
    story.append(KeepTogether(head))
    story.append(table([["Term", "Count", "TF", "IDF", "Score"]] +
                       [[k["term"], k["count"], k["tf"], k["idf"], k["score"]] for k in kw["keywords"][:15]],
                      [0.34, 0.12, 0.18, 0.16, 0.2]))

    # ---- n-grams
    story.append(Paragraph("N-gram analysis", h2))
    for level in a["ngrams"]["levels"][1:]:
        story.append(Paragraph(f"<b>{_p(level['label'])}</b> ({level['distinct']:,} distinct)", body))
        story.append(table([["N-gram", "Count"]] + [[g["ngram"], g["count"]] for g in level["top"][:8]], [0.8, 0.2]))
        story.append(Spacer(1, 4))

    # ---- entities
    en = a["entities"]
    story.append(Paragraph("Named entities", h2))
    if en["groups"]:
        story.append(table([["Label", "Meaning", "Mentions", "Examples"]] +
                           [[g["label"], g["description"], g["total"], ", ".join(e["text"] for e in g["top"][:5])]
                            for g in en["groups"][:10]], [0.12, 0.28, 0.12, 0.48]))
    else:
        story.append(Paragraph("No named entities were found.", body))
    story.append(Paragraph(f"Model: {_p(en['model'])} (trained on news and web text).", small))

    # ---- topic similarity
    ts = a.get("topic_similarity")
    block = [Paragraph("Topic similarity", h2)]
    if ts:
        verdict = f"Best match: <b>{_p(ts['best_topic'])}</b>" if ts["best_topic"] else "No strong topical match"
        block.append(Paragraph(f"{verdict} (cosine {ts['best_similarity']:.3f}). {_p(ts['method'])}", body))
        block.append(chart([t["topic"] for t in ts["similarities"][:8]], [t["similarity"] for t in ts["similarities"][:8]],
                           "Cosine similarity to topic profiles", "cosine similarity", "#7c3aed"))
    else:
        block.append(unavailable(a.get("topic_similarity_error") or "topic profiles"))
    story.append(KeepTogether(block))

    # ---- preprocessing
    pp = a["preprocessing"]
    story.append(Paragraph("Preprocessing pipeline", h2))
    story.append(table([["Stage", "Tokens", "Distinct", "Sample"]] +
                       [[x["name"], f"{x['token_count']:,}", f"{x['unique_count']:,}", " ".join(x["sample"][:8])]
                        for x in pp["stages"]], [0.26, 0.1, 0.1, 0.54]))
    fired = [f"{o['name']}: {o['count']}" for o in pp["cleaning"]["operations"] if o["count"]]
    story.append(Paragraph("Cleaning steps that changed the text: " + (_p("; ".join(fired)) if fired else "none"), small))

    # ---- model evaluation (kept apart from the prediction above)
    story.append(Paragraph("Classifier evaluation (held-out results)", h2))
    story.append(Paragraph(_p(model_service.EVALUATION_NOTE), note))
    ev = payload.get("model_evaluation")
    if ev:
        chosen = ev["selection"]["chosen"]
        story.append(Paragraph(f"Model: {_p(chosen['classifier'])} on {_p(chosen['feature_set'])} features, trained "
                               f"{_p(ev['created_at'])} on {ev['dataset']['train_size']} documents "
                               f"({_p(ev['dataset']['source'])}).", body))
        rows = [["Evaluation set", "Docs", "Accuracy", "Macro-P", "Macro-R", "Macro-F1", "Errors"]]
        for name, e in ev["evaluations"].items():
            if e:
                rows.append([name.replace("_", " "), e["n"], e["accuracy"], e["macro_precision"], e["macro_recall"],
                             e["macro_f1"], len(e["misclassified"])])
        story.append(table(rows, [0.24, 0.12, 0.13, 0.13, 0.13, 0.13, 0.12]))
        story.append(Paragraph(f"Training accuracy ({ev['train_accuracy']}) is measured on the data the model was fitted to "
                               "and is not a performance figure.", small))
        for n in ev["notes"][1:3]:
            story.append(Paragraph(_p(n), small))
    else:
        story.append(unavailable("no training metrics were found (run python -m app.ml.train)"))

    story.append(Paragraph("Limitations", h2))
    for item in LIMITATIONS:
        story.append(Paragraph(_p(item), bullet, bulletText="•"))

    def footer(canvas, pdf_doc):
        canvas.saveState()
        canvas.setFont(f["regular"], 7.5)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(18 * mm, 10 * mm, "Smart Academic Document Analyzer - NLP mini project")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {pdf_doc.page}")
        canvas.restoreState()

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                      title=f"Analysis - {doc_info['filename']}", author="Smart Academic Document Analyzer"
                      ).build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
