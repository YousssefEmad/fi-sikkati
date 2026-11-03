"""Postgres-backed object storage for staging when MinIO/S3 is unreachable.

Keeps identity documents and photos working across API machines without a separate
object store. Presigned URLs point back at the public web origin (proxied to the API)
with an HMAC query signature.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import quote, urlencode

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import Settings
from app.core.database import Database
from app.modules.files.models import ObjectBlob


def _sign(secret: str, *, bucket: str, key: str, exp: int, filename: str) -> str:
    payload = f"{bucket}\n{key}\n{exp}\n{filename}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def verify_object_signature(
    secret: str,
    *,
    bucket: str,
    key: str,
    exp: int,
    filename: str,
    signature: str,
) -> bool:
    if exp < int(time.time()):
        return False
    expected = _sign(secret, bucket=bucket, key=key, exp=exp, filename=filename)
    return hmac.compare_digest(expected, signature)


class DatabaseObjectStorage:
    """Stores objects in Postgres; signed URLs are served by the files router."""

    def __init__(self, settings: Settings) -> None:
        self._database = Database(settings)
        self._secret = settings.auth_hash_secret.get_secret_value()
        self._api_base = str(settings.public_web_url).rstrip("/")
        self._public_bucket = settings.s3_public_bucket

    async def put(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        async with self._database.session_factory() as session:
            stmt = insert(ObjectBlob).values(
                bucket=bucket,
                object_key=key,
                content_type=content_type,
                data=data,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[ObjectBlob.bucket, ObjectBlob.object_key],
                set_={"content_type": content_type, "data": data},
            )
            await session.execute(stmt)
            await session.commit()

    async def delete(self, bucket: str, key: str) -> None:
        async with self._database.session_factory() as session:
            row = await session.get(ObjectBlob, (bucket, key))
            if row is not None:
                await session.delete(row)
                await session.commit()

    async def get(self, bucket: str, key: str) -> tuple[bytes, str] | None:
        async with self._database.session_factory() as session:
            row = await session.scalar(
                select(ObjectBlob).where(
                    ObjectBlob.bucket == bucket, ObjectBlob.object_key == key
                )
            )
            if row is None:
                return None
            return row.data, row.content_type

    async def presigned_get(self, bucket: str, key: str, *, ttl_seconds: int, filename: str) -> str:
        exp = int(time.time()) + max(ttl_seconds, 60)
        safe_name = filename or "document"
        sig = _sign(self._secret, bucket=bucket, key=key, exp=exp, filename=safe_name)
        query = urlencode({"exp": str(exp), "filename": safe_name, "sig": sig})
        return (
            f"{self._api_base}/api/v1/files/objects/"
            f"{quote(bucket, safe='')}/{quote(key, safe='/')}?{query}"
        )

    def public_url(self, bucket: str, key: str) -> str:
        del bucket
        return f"{self._api_base}/api/v1/files/public/{quote(key, safe='/')}"
