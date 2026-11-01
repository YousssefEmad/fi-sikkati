"""Object-storage port. The MinIO adapter and the in-memory test double implement this."""

from __future__ import annotations

from typing import Protocol


class ObjectStorage(Protocol):
    """Bytes in, bytes out. Callers never see bucket credentials or raw keys."""

    async def put(self, bucket: str, key: str, data: bytes, content_type: str) -> None: ...

    async def delete(self, bucket: str, key: str) -> None: ...

    async def presigned_get(
        self, bucket: str, key: str, *, ttl_seconds: int, filename: str
    ) -> str: ...

    def public_url(self, bucket: str, key: str) -> str: ...
