"""Robust text extraction for PDF (PyMuPDF), DOCX (python-docx) and TXT."""
import io
import logging
from dataclasses import dataclass, field

try:  # PyMuPDF >= 1.24 exposes the 'pymupdf' name; older versions only 'fitz'
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore

from docx import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.config import Settings
from app.utils.errors import EmptyDocumentError, MalformedDocumentError

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    text: str
    page_count: int | None
    method: str
    warnings: list[str] = field(default_factory=list)


def _normalise(text: str) -> str:
    """Minimal normalisation only; linguistic cleaning happens in the NLP pipeline."""
    return text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n").strip()


def extract_pdf(content: bytes, settings: Settings) -> ExtractionResult:
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        logger.warning("PDF open failed: %s", exc)
        raise MalformedDocumentError("The PDF is corrupted or cannot be opened.") from exc

    try:
        if doc.needs_pass:
            raise MalformedDocumentError("The PDF is password-protected and cannot be read.")
        total_pages = doc.page_count
        if total_pages == 0:
            raise MalformedDocumentError("The PDF contains no pages.")

        warnings: list[str] = []
        limit = min(total_pages, settings.max_pdf_pages)
        if total_pages > limit:
            warnings.append(
                f"PDF has {total_pages} pages; only the first {limit} were processed."
            )

        parts: list[str] = []
        for index in range(limit):
            try:
                parts.append(doc[index].get_text("text"))
            except Exception as exc:  # one bad page must not kill the whole document
                logger.warning("Failed to read PDF page %d: %s", index + 1, exc)
                warnings.append(f"Page {index + 1} could not be read and was skipped.")
        text = _normalise("\n\n".join(parts))
    finally:
        doc.close()

    if len(text) < settings.min_text_chars:
        raise EmptyDocumentError(
            "No extractable text found. The PDF may be a scanned image "
            "(OCR is not supported in this version)."
        )
    return ExtractionResult(text, total_pages, "pymupdf", warnings)


def _table_to_text(table: Table) -> str:
    rows = []
    for row in table.rows:
        cells: list[str] = []
        for cell in row.cells:
            value = cell.text.strip()
            if value and (not cells or cells[-1] != value):  # merged cells repeat text
                cells.append(value)
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def extract_docx(content: bytes, settings: Settings) -> ExtractionResult:
    try:
        doc = DocxDocument(io.BytesIO(content))
        blocks: list[str] = []
        for block in doc.iter_inner_content():  # preserves document order
            if isinstance(block, Paragraph):
                if block.text.strip():
                    blocks.append(block.text.strip())
            elif isinstance(block, Table):
                table_text = _table_to_text(block)
                if table_text:
                    blocks.append(table_text)
    except Exception as exc:
        logger.warning("DOCX parse failed: %s", exc)
        raise MalformedDocumentError("The DOCX file is corrupted or cannot be parsed.") from exc

    text = _normalise("\n".join(blocks))
    if len(text) < settings.min_text_chars:
        raise EmptyDocumentError("The DOCX document contains no extractable text.")
    return ExtractionResult(text, None, "python-docx")


def extract_txt(content: bytes, settings: Settings) -> ExtractionResult:
    warnings: list[str] = []
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        text, encoding = content.decode("utf-16"), "utf-16"
    else:
        try:
            text, encoding = content.decode("utf-8-sig"), "utf-8"
        except UnicodeDecodeError:
            text, encoding = content.decode("cp1252", errors="replace"), "cp1252"
            warnings.append("File was not valid UTF-8; decoded as Windows-1252.")

    text = _normalise(text)
    if len(text) < settings.min_text_chars:
        raise EmptyDocumentError("The text file is empty or too short to analyse.")
    return ExtractionResult(text, None, f"text:{encoding}", warnings)


def extract_text(file_type: str, content: bytes, settings: Settings) -> ExtractionResult:
    extractors = {"pdf": extract_pdf, "docx": extract_docx, "txt": extract_txt}
    result = extractors[file_type](content, settings)
    logger.info(
        "Extracted %d characters from %s via %s", len(result.text), file_type, result.method
    )
    return result
