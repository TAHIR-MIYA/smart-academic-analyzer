"""Orchestrates validate -> extract -> persist for documents."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Document
from app.services.extraction import extract_text
from app.utils.errors import NotFoundError
from app.utils.file_validation import sanitize_filename, validate_upload

logger = logging.getLogger(__name__)


def create_document(db: Session, filename: str | None, content: bytes, settings: Settings) -> Document:
    safe_name = sanitize_filename(filename)
    file_type = validate_upload(safe_name, content, settings.max_upload_bytes)
    result = extract_text(file_type, content, settings)

    doc = Document(
        original_filename=safe_name,
        file_type=file_type,
        size_bytes=len(content),
        page_count=result.page_count,
        char_count=len(result.text),
        word_count=len(result.text.split()),
        extraction_method=result.method,
        extracted_text=result.text,
        warnings=result.warnings,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    logger.info("Stored document id=%d name='%s'", doc.id, doc.original_filename)
    return doc


def list_documents(db: Session) -> list[Document]:
    return list(db.scalars(select(Document).order_by(Document.created_at.desc(), Document.id.desc())))


def get_document(db: Session, document_id: int) -> Document:
    doc = db.get(Document, document_id)
    if doc is None:
        raise NotFoundError(f"Document {document_id} was not found.")
    return doc


def delete_document(db: Session, document_id: int) -> None:
    doc = get_document(db, document_id)
    db.delete(doc)
    db.commit()
    logger.info("Deleted document id=%d", document_id)
