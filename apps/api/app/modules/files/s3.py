"""MinIO / S3-compatible adapter (ADR-0013)."""

from __future__ import annotations

import asyncio
import io
from datetime import timedelta
from urllib.parse import urlparse

from minio import Minio
from minio.helpers import queryencode

from app.core.config import Settings


def _safe_filename(name: str) -> str:
    cleaned = "".join(ch for ch in name if ch.isprintable() and ch not in {'"', "\\", "\r", "\n"})
    return cleaned[:180] or "document"


class MinioObjectStorage:
    """Puts objects through the MinIO SDK off the event loop."""

    def __init__(self, settings: Settings) -> None:
        parsed = urlparse(settings.s3_endpoint)
        host = parsed.netloc or parsed.path
        secure = settings.s3_use_ssl or parsed.scheme == "https"
        self._client = Minio(
            host,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key.get_secret_value(),
            secure=secure,
            region=settings.s3_region,
        )
        self._public_base = str(settings.s3_public_base_url).rstrip("/")

    async def put(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    async def delete(self, bucket: str, key: str) -> None:
        await asyncio.to_thread(self._client.remove_object, bucket, key)

    async def presigned_get(self, bucket: str, key: str, *, ttl_seconds: int, filename: str) -> str:
        disposition = f'attachment; filename="{_safe_filename(filename)}"'
        return await asyncio.to_thread(
            self._client.presigned_get_object,
            bucket,
            key,
            expires=timedelta(seconds=ttl_seconds),
            response_headers={"response-content-disposition": queryencode(disposition)},
        )

    def public_url(self, bucket: str, key: str) -> str:
        del bucket
        return f"{self._public_base}/{key}"
