"""Run every analysis for a document, save the result, and read it back."""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import AnalysisResult
from app.nlp.pipeline import PreprocessedDocument
from app.services import analysis_service as svc
from app.services import document_service
from app.utils.errors import AppError, NotFoundError, OutdatedAnalysisError

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1  # bump whenever the shape of a saved analysis changes


def _soft(label: str, fn):
    """Run an optional analysis; a failure becomes (None, message) instead of failing the whole report."""
    try:
        return fn(), None
    except AppError as exc:
        logger.info("%s unavailable: %s", label, exc.message)
        return None, exc.message


def build_full_analysis(document, result: PreprocessedDocument, settings: Settings) -> dict:
    classification, classification_error = _soft("classification", lambda: svc.classification_for(result, settings))
    summary, summary_error = _soft("summary", lambda: svc.summary_for(result, settings))
    topic, topic_error = _soft("topic similarity", lambda: svc.topic_similarity_for(result, settings))
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "app_version": settings.app_version,
        "document": {
            "id": document.id, "filename": document.original_filename, "file_type": document.file_type,
            "size_bytes": document.size_bytes, "page_count": document.page_count, "char_count": document.char_count,
            "word_count": document.word_count, "uploaded_at": document.created_at.isoformat(timespec="seconds"),
            "extraction_warnings": list(document.warnings or []),
        },
        "preprocessing": {"document_id": document.id, **result.preprocessing_report()},
        "statistics": result.statistics(),
        "keywords": svc.keywords_for(result, settings, 30),
        "ngrams": svc.ngrams_for(result, 15),
        "entities": svc.entities_for(result),
        "classification": classification, "classification_error": classification_error,
        "summary": summary, "summary_error": summary_error,
        "readability": svc.readability_for(result),
        "vocabulary": svc.vocabulary_for(result),
        "topic_similarity": topic, "topic_similarity_error": topic_error,
    }


def run_and_store(db: Session, document_id: int, settings: Settings) -> dict:
    document = document_service.get_document(db, document_id)
    result = svc.preprocess_text(document.extracted_text, settings)
    analysis = build_full_analysis(document, result, settings)

    row = db.scalar(select(AnalysisResult).where(AnalysisResult.document_id == document_id))
    if row is None:
        db.add(AnalysisResult(document_id=document_id, schema_version=SCHEMA_VERSION, result=analysis))
    else:
        row.schema_version, row.result = SCHEMA_VERSION, analysis
    db.commit()
    logger.info("Saved analysis for document id=%d", document_id)
    return analysis


def get_stored(db: Session, document_id: int) -> dict:
    document_service.get_document(db, document_id)  # 404 for an unknown document
    row = db.scalar(select(AnalysisResult).where(AnalysisResult.document_id == document_id))
    if row is None:
        raise NotFoundError(
            f"Document {document_id} has not been analysed yet.",
            details={"fix": f"POST /api/analysis/{document_id}"},
        )
    if row.schema_version != SCHEMA_VERSION:
        raise OutdatedAnalysisError(
            "The saved analysis was created by an older version of the application; run the analysis again.",
            details={"fix": f"POST /api/analysis/{document_id}"},
        )
    return row.result


def get_or_run(db: Session, document_id: int, settings: Settings, refresh: bool = False) -> dict:
    """Saved analysis if there is a current one, otherwise run (and save) a new one."""
    document_service.get_document(db, document_id)  # unknown document -> 404, never silently analysed
    if not refresh:
        try:
            return get_stored(db, document_id)
        except (NotFoundError, OutdatedAnalysisError):
            pass  # nothing usable saved: fall through and analyse
    return run_and_store(db, document_id, settings)


def analysed_document_ids(db: Session) -> set[int]:
    return set(db.scalars(select(AnalysisResult.document_id)))


def all_stored(db: Session) -> list[dict]:
    return [row.result for row in db.scalars(select(AnalysisResult)) if row.schema_version == SCHEMA_VERSION]
