"""Serve staging object blobs (signed private docs + public media)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError
from app.modules.files.database_storage import DatabaseObjectStorage, verify_object_signature
from app.modules.files.dependencies import get_object_storage
from app.modules.files.ports import ObjectStorage

router = APIRouter(prefix="/files", tags=["files"])


def _as_db_storage(storage: ObjectStorage) -> DatabaseObjectStorage | None:
    return storage if isinstance(storage, DatabaseObjectStorage) else None


@router.get(
    "/objects/{bucket}/{key:path}",
    operation_id="files_signed_object",
    summary="Download a signed private object (HMAC query)",
    include_in_schema=False,
)
async def signed_object(
    bucket: str,
    key: str,
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    settings: Annotated[Settings, Depends(get_settings)],
    exp: Annotated[int, Query()],
    sig: Annotated[str, Query()],
    filename: Annotated[str, Query()] = "document",
) -> Response:
    db_storage = _as_db_storage(storage)
    if db_storage is None:
        raise NotFoundError("Document not found.")
    if not verify_object_signature(
        settings.auth_hash_secret.get_secret_value(),
        bucket=bucket,
        key=key,
        exp=exp,
        filename=filename,
        signature=sig,
    ):
        raise NotFoundError("Document not found.")
    payload = await db_storage.get(bucket, key)
    if payload is None:
        raise NotFoundError("Document not found.")
    data, content_type = payload
    headers = {
        "Content-Disposition": f'attachment; filename="{filename.replace(chr(34), "")}"',
        "Cache-Control": "private, max-age=60",
    }
    return Response(content=data, media_type=content_type, headers=headers)


@router.get(
    "/public/{key:path}",
    operation_id="files_public_object",
    summary="Fetch a public-media object",
    include_in_schema=False,
)
async def public_object(
    key: str,
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    db_storage = _as_db_storage(storage)
    if db_storage is None:
        raise NotFoundError("File not found.")
    payload = await db_storage.get(settings.s3_public_bucket, key)
    if payload is None:
        raise NotFoundError("File not found.")
    data, content_type = payload
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
