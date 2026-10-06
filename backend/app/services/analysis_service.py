"""Runs NLP analyses for stored documents or raw text."""
import logging

from sqlalchemy.orm import Session

from app.config import Settings
from app.ml.predict import classify, load_bundle
from app.nlp.ner import extract_entities_cached
from app.nlp.ngrams import analyse_ngrams
from app.nlp.pipeline import PreprocessedDocument, run_pipeline_cached
from app.nlp.readability import analyse_readability
from app.nlp.similarity import compare_documents, load_topics, topic_similarity
from app.nlp.summarizer import summarize
from app.nlp.vocabulary import analyse_vocabulary
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


# ---- Module 5 ----
def summary_for(result: PreprocessedDocument, settings: Settings, num_sentences: int | None = None) -> dict:
    # Sentence scores reuse the keyword TF-IDF weights, so the summary and the Keywords page agree.
    kw = keywords_for(result, settings, top_k=10**6)
    weights = {k["term"]: k["score"] for k in kw["keywords"]}
    return summarize(result, weights, kw["idf_mode"], num_sentences)


def readability_for(result: PreprocessedDocument) -> dict:
    return analyse_readability(result)


def vocabulary_for(result: PreprocessedDocument) -> dict:
    return analyse_vocabulary(result)


def topic_similarity_for(result: PreprocessedDocument, settings: Settings) -> dict:
    """Raises NLPResourceError (HTTP 503) if no topic profile files exist."""
    return topic_similarity(result, load_topics(settings.topics_dir))


def compare_stored_documents(db: Session, id_a: int, id_b: int, settings: Settings) -> dict:
    from app.utils.errors import NLPResourceError

    doc_a = document_service.get_document(db, id_a)
    doc_b = document_service.get_document(db, id_b)
    a = run_pipeline_cached(doc_a.extracted_text, settings.max_analysis_chars)
    b = run_pipeline_cached(doc_b.extracted_text, settings.max_analysis_chars)
    try:
        topics = load_topics(settings.topics_dir)
    except NLPResourceError:  # comparison still works, only the IDF corpus is smaller
        topics = []
    out = compare_documents(a, b, topics)
    out["document_a"] = {"id": doc_a.id, "filename": doc_a.original_filename}
    out["document_b"] = {"id": doc_b.id, "filename": doc_b.original_filename}
    return out
