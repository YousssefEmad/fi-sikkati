"""Tiny valid files for upload tests."""

from __future__ import annotations

import io

from PIL import Image


def jpeg_bytes(
    *, size: tuple[int, int] = (32, 24), color: tuple[int, int, int] = (20, 40, 80)
) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), (200, 10, 10)).save(buffer, format="PNG")
    return buffer.getvalue()


SAFE_PDF = b"%PDF-1.4\n1 0 obj<< /Type /Catalog >>endobj\ntrailer<<>>\n%%EOF\n"
SCRIPT_PDF = b"%PDF-1.4\n1 0 obj<</JavaScript (alert(1))>>endobj\ntrailer<<>>\n%%EOF\n"
