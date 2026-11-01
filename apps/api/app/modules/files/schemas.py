"""HTTP shapes for file metadata (never the bytes)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.core.schemas import ApiModel
from app.modules.files.models import ScanStatus


class FileMetaResponse(ApiModel):
    id: UUID
    original_name: str
    mime_type: str
    byte_size: int
    scan_status: ScanStatus
    created_at: datetime


class SignedUrlResponse(ApiModel):
    url: str
    expires_in_seconds: int
