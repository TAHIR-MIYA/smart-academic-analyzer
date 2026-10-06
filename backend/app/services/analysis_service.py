"""Runs NLP analyses for stored documents or raw text."""
import logging

from sqlalchemy.orm import Session

from app.config import Settings
from app.ml.predict import classify, load_bundle
from app.nlp.ner import extract_entities_cached
from app.nlp.ngrams import analyse_ngrams
from app.nlp.pipeline import PreprocessedDocument, run_pipeline_cached
from app.nlp.tfidf import extract_keywords, load_reference_idf
from app.services import document_service

logger = logging.getLogger(__name__)


def preprocess_document(db: Session, document_id: int, settings: Settings) -> tuple[int, PreprocessedDocument]:
    doc = document_service.get_document(db, document_id)
    return doc.id, run_pipeline_cached(doc.extracted_text, settings.max_analysis_chars)


def preprocess_text(text: str, settings: Settings) -> PreprocessedDocument:
    return run_pipeline_cached(text, settings.max_analysis_chars)


# ---- building blocks shared by the document endpoints and the preview endpoint ----
def keywords_for(result: PreprocessedDocument, settings: Settings, top_k: int = 20) -> dict:
    reference = load_reference_idf(settings.reference_idf_path)
    return extract_keywords(result, reference, top_k)


def ngrams_for(result: PreprocessedDocument, top_k: int = 15) -> dict:
    return analyse_ngrams(result, top_k)


def entities_for(result: PreprocessedDocument) -> dict:
    return extract_entities_cached(result.cleaned_text)


def classification_for(result: PreprocessedDocument, settings: Settings) -> dict:
    """Raises ModelNotTrainedError (HTTP 503) if the classifier has not been trained or cannot be loaded."""
    bundle = load_bundle(settings.model_path)
    return classify(result, bundle, settings.classification_min_confidence)
