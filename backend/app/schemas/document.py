from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    file_type: str
    size_bytes: int
    page_count: int | None
    char_count: int
    word_count: int
    extraction_method: str
    warnings: list[str]
    created_at: datetime
    analyzed: bool = False  # a saved analysis exists for this document


class DocumentDetail(DocumentSummary):
    extracted_text: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict | list | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
