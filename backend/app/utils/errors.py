"""Application-specific exceptions. Each maps to an HTTP status and a stable error code."""
from typing import Any, Optional


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.details = details


class InvalidFileError(AppError):
    status_code = 400
    code = "invalid_file"


class UnsupportedFileTypeError(AppError):
    status_code = 415
    code = "unsupported_file_type"


class FileTooLargeError(AppError):
    status_code = 413
    code = "file_too_large"


class EmptyDocumentError(AppError):
    status_code = 422
    code = "empty_document"


class MalformedDocumentError(AppError):
    status_code = 422
    code = "malformed_document"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class NLPResourceError(AppError):
    status_code = 503
    code = "nlp_resources_missing"
