"""In-memory object storage used by the test suite (same idea as ``RecordingEmailSender``)."""

from __future__ import annotations

from urllib.parse import quote


class MemoryObjectStorage:
    """Keeps objects in a dict. Presigned URLs are deterministic ``memory://`` locators."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], tuple[bytes, str]] = {}
        self.deleted: list[tuple[str, str]] = []

    async def put(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        self.objects[(bucket, key)] = (data, content_type)

    async def delete(self, bucket: str, key: str) -> None:
        self.objects.pop((bucket, key), None)
        self.deleted.append((bucket, key))

    async def presigned_get(self, bucket: str, key: str, *, ttl_seconds: int, filename: str) -> str:
        return f"memory://{bucket}/{key}?ttl={ttl_seconds}&filename={quote(filename, safe='')}"

    def public_url(self, bucket: str, key: str) -> str:
        return f"memory://{bucket}/{key}"

    def get(self, bucket: str, key: str) -> tuple[bytes, str] | None:
        return self.objects.get((bucket, key))
