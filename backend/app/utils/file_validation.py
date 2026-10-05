"""Upload validation: extension, size, emptiness and magic-byte (content) checks.

The file extension alone is never trusted: a renamed .exe must not pass as .pdf.
"""
import codecs
import logging
import re
from pathlib import Path

from app.utils.errors import (
    FileTooLargeError,
    InvalidFileError,
    UnsupportedFileTypeError,
)

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf": "pdf", ".docx": "docx", ".txt": "txt"}
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_filename(filename: str | None) -> str:
    """Strip any directory part and control characters; cap length."""
    if not filename:
        raise InvalidFileError("No file name was provided.")
    name = Path(filename.replace("\\", "/")).name
    name = _CONTROL_CHARS.sub("", name).strip()
    if not name:
        raise InvalidFileError("The file name is invalid.")
    return name[:255]


def validate_upload(filename: str, content: bytes, max_bytes: int) -> str:
    """Return the normalised file type ('pdf' | 'docx' | 'txt') or raise an AppError."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{ext or 'none'}'. Allowed types: PDF, DOCX, TXT.",
            details={"allowed": sorted(ALLOWED_EXTENSIONS)},
        )
    file_type = ALLOWED_EXTENSIONS[ext]

    if len(content) == 0:
        raise InvalidFileError("The uploaded file is empty (0 bytes).")
    if len(content) > max_bytes:
        raise FileTooLargeError(
            f"File exceeds the maximum allowed size of {max_bytes / (1024 * 1024):.2f} MB."
        )

    if file_type == "pdf" and b"%PDF-" not in content[:1024]:
        raise InvalidFileError("File content is not a valid PDF (missing PDF header).")
    if file_type == "docx" and not content.startswith(b"PK\x03\x04"):
        raise InvalidFileError("File content is not a valid DOCX (not a ZIP container).")
    if file_type == "txt":
        is_utf16 = content.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE))
        if not is_utf16 and b"\x00" in content[:8192]:
            raise InvalidFileError("File looks like binary data, not plain text.")

    logger.info("Validated upload '%s' (%s, %d bytes)", filename, file_type, len(content))
    return file_type
