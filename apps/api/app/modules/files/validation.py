"""Upload sniffing and sanitising (security.md §3).

Pillow re-encodes images so EXIF/GPS and polyglot payloads are stripped. PDFs are accepted only
when they look like a PDF and do not advertise JavaScript or embedded files. ``python-magic`` is
intentionally not used: it is painful on Windows and the magic-byte checks cover the allow-list.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import PurePosixPath

from PIL import Image, UnidentifiedImageError

from app.core.errors import FileTooLargeError, UnsupportedFileTypeError, ValidationAppError

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({"jpg", "jpeg", "png", "pdf"})
IMAGE_EXTENSIONS: frozenset[str] = frozenset({"jpg", "jpeg", "png"})
_MIME_BY_EXTENSION: dict[str, str] = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "pdf": "application/pdf",
}
_PDF_REJECT_MARKERS: tuple[bytes, ...] = (
    b"/javascript",
    b"/js ",
    b"/js(",
    b"/js<",
    b"/embeddedfile",
    b"/launch",
    b"/richmedia",
)
_MAX_IMAGE_EDGE = 4096
_PHOTO_MAX_EDGE = 1024


@dataclass(frozen=True, slots=True)
class SanitisedUpload:
    """Bytes that have been sniffed, re-encoded when needed, and given a safe name."""

    data: bytes
    mime_type: str
    extension: str
    original_name: str


def sanitise_filename(name: str | None) -> str:
    raw = (name or "document").replace("\\", "/").split("/")[-1].strip()
    cleaned = "".join(
        ch for ch in raw if ch.isprintable() and ch not in {":", "*", "?", '"', "<", ">", "|"}
    )
    return cleaned[:200] or "document"


def extension_of(filename: str) -> str:
    suffix = PurePosixPath(filename).suffix.lower().lstrip(".")
    return "jpg" if suffix == "jpeg" else suffix


def sniff_mime(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def _reject_dangerous_pdf(data: bytes) -> None:
    lowered = data.lower()
    if any(marker in lowered for marker in _PDF_REJECT_MARKERS):
        raise UnsupportedFileTypeError(
            "PDFs that contain scripts or embedded files are not allowed."
        )


def _reencode_image(data: bytes, *, mime: str, max_edge: int) -> tuple[bytes, str]:
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise UnsupportedFileTypeError("The image could not be read.") from exc
    image.thumbnail((max_edge, max_edge))
    buffer = io.BytesIO()
    if mime == "image/png":
        converted = (
            image.convert("RGBA") if image.mode in {"P", "RGBA", "LA"} else image.convert("RGB")
        )
        converted.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue(), "image/png"
    image.convert("RGB").save(buffer, format="JPEG", quality=85, optimize=True)
    return buffer.getvalue(), "image/jpeg"


def sanitise_upload(
    data: bytes,
    *,
    filename: str | None,
    max_bytes: int,
    images_only: bool = False,
    photo: bool = False,
) -> SanitisedUpload:
    """Validate size, extension and magic bytes; return stored bytes and the canonical MIME."""
    if not data:
        raise ValidationAppError("The file is empty.")
    if len(data) > max_bytes:
        raise FileTooLargeError(f"Files must be {max_bytes} bytes or smaller.")

    original_name = sanitise_filename(filename)
    extension = extension_of(original_name)
    if extension not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError("Allowed types are JPEG, PNG and PDF.")
    if (images_only or photo) and extension not in IMAGE_EXTENSIONS:
        raise UnsupportedFileTypeError("This upload must be a JPEG or PNG image.")

    sniffed = sniff_mime(data)
    expected = _MIME_BY_EXTENSION[extension]
    if sniffed is None or sniffed != expected:
        raise UnsupportedFileTypeError("The file contents do not match the file extension.")

    if sniffed == "application/pdf":
        _reject_dangerous_pdf(data)
        stored, mime = data, sniffed
        stored_ext = "pdf"
    else:
        stored, mime = _reencode_image(
            data, mime=sniffed, max_edge=_PHOTO_MAX_EDGE if photo else _MAX_IMAGE_EDGE
        )
        stored_ext = "jpg" if mime == "image/jpeg" else "png"
        if len(stored) > max_bytes:
            raise FileTooLargeError(f"Files must be {max_bytes} bytes or smaller.")

    return SanitisedUpload(
        data=stored, mime_type=mime, extension=stored_ext, original_name=original_name
    )
