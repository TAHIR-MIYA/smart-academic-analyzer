import pytest

from app.utils.errors import (
    FileTooLargeError,
    InvalidFileError,
    UnsupportedFileTypeError,
)
from app.utils.file_validation import sanitize_filename, validate_upload

MAX = 1024 * 1024


def test_valid_types_are_recognised(make_pdf, make_docx):
    assert validate_upload("a.PDF", make_pdf(["hello world text"]), MAX) == "pdf"
    assert validate_upload("a.docx", make_docx(["hello world text"]), MAX) == "docx"
    assert validate_upload("a.txt", b"plain text here", MAX) == "txt"


@pytest.mark.parametrize("name", ["virus.exe", "image.png", "noextension", "archive.tar.gz"])
def test_unsupported_extension(name):
    with pytest.raises(UnsupportedFileTypeError):
        validate_upload(name, b"data", MAX)


def test_empty_file_rejected():
    with pytest.raises(InvalidFileError):
        validate_upload("a.txt", b"", MAX)


def test_oversized_file_rejected():
    with pytest.raises(FileTooLargeError):
        validate_upload("a.txt", b"x" * 2000, 1000)


def test_pdf_extension_with_wrong_content_rejected():
    with pytest.raises(InvalidFileError):
        validate_upload("fake.pdf", b"this is not a pdf at all", MAX)


def test_docx_extension_with_wrong_content_rejected():
    with pytest.raises(InvalidFileError):
        validate_upload("fake.docx", b"this is not a zip", MAX)


def test_binary_txt_rejected():
    with pytest.raises(InvalidFileError):
        validate_upload("bin.txt", b"abc\x00\x01\x02def", MAX)


def test_utf16_txt_allowed():
    assert validate_upload("u.txt", "hello world".encode("utf-16"), MAX) == "txt"


def test_filename_sanitised():
    assert sanitize_filename("../../etc/passwd.txt") == "passwd.txt"
    assert sanitize_filename("C:\\Users\\me\\notes.txt") == "notes.txt"
    with pytest.raises(InvalidFileError):
        sanitize_filename(None)
    with pytest.raises(InvalidFileError):
        sanitize_filename("   ")
