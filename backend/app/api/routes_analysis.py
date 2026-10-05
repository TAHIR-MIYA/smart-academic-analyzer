from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_db
from app.schemas.analysis import (
    EntitiesResponse,
    KeywordsResponse,
    NgramsResponse,
    PreprocessingResponse,
    PreviewRequest,
    PreviewResponse,
    StatisticsResponse,
)
from app.schemas.document import ErrorResponse
from app.services import analysis_service as svc

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


@router.post("/preview", response_model=PreviewResponse, responses=_errors)
def preview_text(body: PreviewRequest, settings: Settings = Depends(get_settings)):
    """Run the analyses on pasted text (nothing is stored). Handy for live viva demos."""
    result = svc.preprocess_text(body.text, settings)
    return PreviewResponse(
        preprocessing=PreprocessingResponse(**result.preprocessing_report()),
        statistics=result.statistics(),
        keywords=svc.keywords_for(result, settings),
        ngrams=svc.ngrams_for(result),
        entities=svc.entities_for(result),
    )
