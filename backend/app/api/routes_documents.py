from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_db
from app.schemas.document import DocumentDetail, DocumentSummary, ErrorResponse
from app.services import analysis_store, document_service

router = APIRouter(prefix="/api/documents", tags=["documents"])

_errors = {
    400: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    415: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


# Plain 'def' (not 'async def'): FastAPI runs it in a worker thread, so CPU-heavy
# extraction does not block the event loop.
@router.post("/upload", response_model=DocumentDetail, status_code=201, responses=_errors)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    # Read at most limit+1 bytes so an oversized upload is detected without loading it all.
    content = file.file.read(settings.max_upload_bytes + 1)
    return document_service.create_document(db, file.filename, content, settings)


@router.get("", response_model=list[DocumentSummary])
def list_documents(db: Session = Depends(get_db)):
    docs = document_service.list_documents(db)
    analysed = analysis_store.analysed_document_ids(db)
    for doc in docs:
        doc.analyzed = doc.id in analysed  # plain attribute, not a column
    return docs


@router.get("/{document_id}", response_model=DocumentDetail, responses={404: {"model": ErrorResponse}})
def get_document(document_id: int, db: Session = Depends(get_db)):
    doc = document_service.get_document(db, document_id)
    doc.analyzed = document_id in analysis_store.analysed_document_ids(db)
    return doc


@router.delete("/{document_id}", status_code=204, responses={404: {"model": ErrorResponse}})
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document_service.delete_document(db, document_id)
    return Response(status_code=204)
