"""Runs NLP analyses for stored documents or raw text."""
import logging

from sqlalchemy.orm import Session

from app.config import Settings
from app.nlp.pipeline import PreprocessedDocument, run_pipeline_cached
from app.services import document_service

logger = logging.getLogger(__name__)


def preprocess_document(db: Session, document_id: int, settings: Settings) -> tuple[int, PreprocessedDocument]:
    doc = document_service.get_document(db, document_id)
    return doc.id, run_pipeline_cached(doc.extracted_text, settings.max_analysis_chars)


def preprocess_text(text: str, settings: Settings) -> PreprocessedDocument:
    return run_pipeline_cached(text, settings.max_analysis_chars)
