from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_db
from app.schemas.document import ErrorResponse
from app.services import export_service

router = APIRouter(prefix="/api/export", tags=["export"])

_MEDIA = {"json": "application/json", "pdf": "application/pdf"}


@router.get("/{document_id}", responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
            response_class=Response)
def export_analysis(
    document_id: int,
    format: Literal["json", "pdf"] = Query("json", description="Download format"),
    refresh: bool = Query(False, description="Re-run the analysis instead of using the saved one"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Download the analysis as JSON or as a PDF report. The analysis is run (and saved) if none exists yet."""
    payload = export_service.build_export_payload(db, document_id, settings, refresh)
    content = export_service.export_json(payload) if format == "json" else export_service.build_pdf(payload)
    name = export_service.download_name(payload["analysis"]["document"]["filename"], document_id, format)
    return Response(content=content, media_type=_MEDIA[format],
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})
