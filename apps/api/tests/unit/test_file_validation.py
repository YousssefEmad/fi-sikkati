from __future__ import annotations

import pytest

from app.core.errors import FileTooLargeError, UnsupportedFileTypeError, ValidationAppError
from app.modules.files.validation import sanitise_upload
from tests.support.uploads import SAFE_PDF, SCRIPT_PDF, jpeg_bytes, png_bytes


def test_jpeg_is_reencoded_and_stripped() -> None:
    result = sanitise_upload(jpeg_bytes(), filename="id.jpg", max_bytes=1_000_000)
    assert result.mime_type == "image/jpeg"
    assert result.extension == "jpg"
    assert result.data.startswith(b"\xff\xd8\xff")


def test_png_stays_png() -> None:
    result = sanitise_upload(png_bytes(), filename="shot.png", max_bytes=1_000_000)
    assert result.mime_type == "image/png"
    assert result.data.startswith(b"\x89PNG")


def test_safe_pdf_is_accepted() -> None:
    result = sanitise_upload(SAFE_PDF, filename="licence.pdf", max_bytes=1_000_000)
    assert result.mime_type == "application/pdf"


def test_javascript_pdf_is_rejected() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        sanitise_upload(SCRIPT_PDF, filename="licence.pdf", max_bytes=1_000_000)


def test_extension_must_match_bytes() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        sanitise_upload(jpeg_bytes(), filename="id.png", max_bytes=1_000_000)


def test_empty_file_is_rejected() -> None:
    with pytest.raises(ValidationAppError):
        sanitise_upload(b"", filename="id.jpg", max_bytes=1_000_000)


def test_oversized_file_is_rejected() -> None:
    with pytest.raises(FileTooLargeError):
        sanitise_upload(jpeg_bytes(), filename="id.jpg", max_bytes=10)


def test_selfie_rejects_pdf() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        sanitise_upload(SAFE_PDF, filename="face.pdf", max_bytes=1_000_000, images_only=True)
