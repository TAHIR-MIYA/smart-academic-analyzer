from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_db
from app.schemas.analysis import (
    FullAnalysisResponse,
    CompareRequest,
    ComparisonResponse,
    PreviewFull,
    ReadabilityResponse,
    SummaryResponse,
    TopicSimilarityResponse,
    VocabularyResponse,
    ClassificationResponse,
    EntitiesResponse,
    KeywordsResponse,
    NgramsResponse,
    PreprocessingResponse,
    PreviewRequest,
    StatisticsResponse,
)
from app.schemas.document import ErrorResponse
from app.services import analysis_service as svc
from app.services import analysis_store
from app.utils.errors import ModelNotTrainedError, NLPResourceError

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

_errors = {404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


@router.get("/{document_id}/preprocessing", response_model=PreprocessingResponse, responses=_errors)
def get_preprocessing(
    document_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    doc_id, result = svc.preprocess_document(db, document_id, settings)
    return PreprocessingResponse(document_id=doc_id, **result.preprocessing_report())


@router.get("/{document_id}/statistics", response_model=StatisticsResponse, responses=_errors)
def get_statistics(
    document_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    doc_id, result = svc.preprocess_document(db, document_id, settings)
    return StatisticsResponse(document_id=doc_id, statistics=result.statistics())


@router.get("/{document_id}/keywords", response_model=KeywordsResponse, responses=_errors)
def get_keywords(
    document_id: int,
    top_k: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    doc_id, result = svc.preprocess_document(db, document_id, settings)
    return KeywordsResponse(document_id=doc_id, **svc.keywords_for(result, settings, top_k))


@router.get("/{document_id}/ngrams", response_model=NgramsResponse, responses=_errors)
def get_ngrams(
    document_id: int,
    top_k: int = Query(15, ge=1, le=100),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    doc_id, result = svc.preprocess_document(db, document_id, settings)
    return NgramsResponse(document_id=doc_id, **svc.ngrams_for(result, top_k))


@router.get("/{document_id}/entities", response_model=EntitiesResponse, responses=_errors)
def get_entities(
    document_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    doc_id, result = svc.preprocess_document(db, document_id, settings)
    return EntitiesResponse(document_id=doc_id, **svc.entities_for(result))


@router.get("/{document_id}/classification", response_model=ClassificationResponse, responses=_errors)
def get_classification(
    document_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    doc_id, result = svc.preprocess_document(db, document_id, settings)
    return ClassificationResponse(document_id=doc_id, **svc.classification_for(result, settings))


@router.get("/{document_id}/summary", response_model=SummaryResponse, responses=_errors)
def get_summary(
    document_id: int,
    sentences: int | None = Query(None, ge=1, le=20, description="Number of sentences; default is about 25 % of the document"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    doc_id, result = svc.preprocess_document(db, document_id, settings)
    return SummaryResponse(document_id=doc_id, **svc.summary_for(result, settings, sentences))


@router.get("/{document_id}/readability", response_model=ReadabilityResponse, responses=_errors)
def get_readability(
    document_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    doc_id, result = svc.preprocess_document(db, document_id, settings)
    return ReadabilityResponse(document_id=doc_id, **svc.readability_for(result))


@router.get("/{document_id}/vocabulary", response_model=VocabularyResponse, responses=_errors)
def get_vocabulary(
    document_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    doc_id, result = svc.preprocess_document(db, document_id, settings)
    return VocabularyResponse(document_id=doc_id, **svc.vocabulary_for(result))


@router.get("/{document_id}/similarity", response_model=TopicSimilarityResponse, responses=_errors)
def get_topic_similarity(
    document_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    doc_id, result = svc.preprocess_document(db, document_id, settings)
    return TopicSimilarityResponse(document_id=doc_id, **svc.topic_similarity_for(result, settings))


@router.post("/compare", response_model=ComparisonResponse, responses=_errors)
def compare_documents(body: CompareRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    """Cosine similarity, vocabulary overlap and the most similar sentence pairs of two stored documents."""
    return ComparisonResponse(**svc.compare_stored_documents(db, body.document_a, body.document_b, settings))


@router.post("/preview", response_model=PreviewFull, responses=_errors)
def preview_text(body: PreviewRequest, settings: Settings = Depends(get_settings)):
    """Run the analyses on pasted text (nothing is stored). Handy for live viva demos."""
    result = svc.preprocess_text(body.text, settings)
    classification, classification_error = None, None
    try:  # a missing model must not break the other analyses
        classification = svc.classification_for(result, settings)
    except ModelNotTrainedError as exc:
        classification_error = exc.message
    topic, topic_error = None, None
    try:
        topic = svc.topic_similarity_for(result, settings)
    except NLPResourceError as exc:
        topic_error = exc.message
    return PreviewFull(
        preprocessing=PreprocessingResponse(**result.preprocessing_report()),
        statistics=result.statistics(),
        keywords=svc.keywords_for(result, settings),
        ngrams=svc.ngrams_for(result),
        entities=svc.entities_for(result),
        classification=classification,
        classification_error=classification_error,
        summary=svc.summary_for(result, settings),
        readability=svc.readability_for(result),
        vocabulary=svc.vocabulary_for(result),
        topic_similarity=topic,
        topic_similarity_error=topic_error,
    )


# NOTE: the two routes below take a bare {document_id}; they must stay AFTER the literal paths
# /compare and /preview, otherwise "compare" would be matched as a document id.
@router.post("/{document_id}", response_model=FullAnalysisResponse, responses={**_errors, 409: {"model": ErrorResponse}})
def run_analysis(document_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    """Run every analysis for a stored document and save the result (replacing any earlier one)."""
    return analysis_store.run_and_store(db, document_id, settings)


@router.get("/{document_id}", response_model=FullAnalysisResponse, responses={**_errors, 409: {"model": ErrorResponse}})
def get_saved_analysis(document_id: int, db: Session = Depends(get_db)):
    """The saved analysis; 404 if it has not been run yet, 409 if it was saved by an older version."""
    return analysis_store.get_stored(db, document_id)
