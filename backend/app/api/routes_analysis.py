from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_db
from app.schemas.analysis import (
    PreprocessingResponse,
    PreviewRequest,
    PreviewResponse,
    StatisticsResponse,
)
from app.schemas.document import ErrorResponse
from app.services import analysis_service

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

_errors = {404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


@router.get("/{document_id}/preprocessing", response_model=PreprocessingResponse, responses=_errors)
def get_preprocessing(
    document_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    doc_id, result = analysis_service.preprocess_document(db, document_id, settings)
    return PreprocessingResponse(document_id=doc_id, **result.preprocessing_report())


@router.get("/{document_id}/statistics", response_model=StatisticsResponse, responses=_errors)
def get_statistics(
    document_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    doc_id, result = analysis_service.preprocess_document(db, document_id, settings)
    return StatisticsResponse(document_id=doc_id, statistics=result.statistics())


@router.post("/preview", response_model=PreviewResponse, responses=_errors)
def preview_text(body: PreviewRequest, settings: Settings = Depends(get_settings)):
    """Run the pipeline on pasted text (nothing is stored). Handy for live viva demos."""
    result = analysis_service.preprocess_text(body.text, settings)
    return PreviewResponse(
        preprocessing=PreprocessingResponse(**result.preprocessing_report()),
        statistics=result.statistics(),
    )
