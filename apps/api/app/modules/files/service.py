"""Store, sign and purge files (ADR-0013, BR-VER-04, BR-VER-06)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.ids import uuid7
from app.modules.audit.models import ActorType, AuditAction
from app.modules.audit.service import AuditLogWriter
from app.modules.files.models import ScanStatus, StorageBucket, StoredFile
from app.modules.files.ports import ObjectStorage
from app.modules.files.repository import FileRepository
from app.modules.files.validation import sanitise_upload


@dataclass(frozen=True, slots=True)
class StoredFileView:
    id: UUID
    owner_user_id: UUID
    bucket: StorageBucket
    object_key: str
    mime_type: str
    byte_size: int
    original_name: str
    scan_status: ScanStatus
    purge_after: datetime | None
    purged_at: datetime | None
    created_at: datetime
    public_url: str | None


@dataclass(frozen=True, slots=True)
class SignedDownload:
    url: str
    expires_in_seconds: int


def _view(row: StoredFile, public_url: str | None = None) -> StoredFileView:
    return StoredFileView(
        id=row.id,
        owner_user_id=row.owner_user_id,
        bucket=row.bucket,
        object_key=row.object_key,
        mime_type=row.mime_type,
        byte_size=row.byte_size,
        original_name=row.original_name,
        scan_status=row.scan_status,
        purge_after=row.purge_after,
        purged_at=row.purged_at,
        created_at=row.created_at,
        public_url=public_url,
    )


class FileService:
    def __init__(
        self,
        repository: FileRepository,
        storage: ObjectStorage,
        settings: Settings,
        audit: AuditLogWriter,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._settings = settings
        self._audit = audit

    def _bucket_name(self, bucket: StorageBucket) -> str:
        if bucket is StorageBucket.PUBLIC_MEDIA:
            return self._settings.s3_public_bucket
        return self._settings.s3_private_bucket

    async def get(self, file_id: UUID) -> StoredFileView:
        row = await self._require(file_id)
        url = None
        if row.bucket is StorageBucket.PUBLIC_MEDIA and row.purged_at is None:
            url = self._storage.public_url(self._bucket_name(row.bucket), row.object_key)
        return _view(row, url)

    async def public_url_for(self, file_id: UUID) -> str | None:
        row = await self._repository.get(file_id)
        if row is None or row.purged_at is not None or row.bucket is not StorageBucket.PUBLIC_MEDIA:
            return None
        return self._storage.public_url(self._bucket_name(row.bucket), row.object_key)

    async def store_private_document(
        self,
        *,
        owner_user_id: UUID,
        data: bytes,
        filename: str | None,
        images_only: bool = False,
        actor_id: UUID,
        request_id: str | None,
    ) -> StoredFileView:
        sanitised = sanitise_upload(
            data,
            filename=filename,
            max_bytes=self._settings.uploads_max_document_bytes,
            images_only=images_only,
        )
        return await self._store(
            owner_user_id=owner_user_id,
            sanitised_data=sanitised.data,
            mime_type=sanitised.mime_type,
            extension=sanitised.extension,
            original_name=sanitised.original_name,
            bucket=StorageBucket.PRIVATE_DOCUMENTS,
            prefix="documents",
            actor_id=actor_id,
            request_id=request_id,
        )

    async def store_public_photo(
        self,
        *,
        owner_user_id: UUID,
        data: bytes,
        filename: str | None,
        actor_id: UUID,
        request_id: str | None,
    ) -> StoredFileView:
        sanitised = sanitise_upload(
            data,
            filename=filename,
            max_bytes=self._settings.uploads_max_document_bytes,
            images_only=True,
            photo=True,
        )
        return await self._store(
            owner_user_id=owner_user_id,
            sanitised_data=sanitised.data,
            mime_type=sanitised.mime_type,
            extension=sanitised.extension,
            original_name=sanitised.original_name,
            bucket=StorageBucket.PUBLIC_MEDIA,
            prefix="photos",
            actor_id=actor_id,
            request_id=request_id,
        )

    async def _store(
        self,
        *,
        owner_user_id: UUID,
        sanitised_data: bytes,
        mime_type: str,
        extension: str,
        original_name: str,
        bucket: StorageBucket,
        prefix: str,
        actor_id: UUID,
        request_id: str | None,
    ) -> StoredFileView:
        file_id = uuid7()
        key = f"{prefix}/{owner_user_id}/{file_id}.{extension}"
        digest = hashlib.sha256(sanitised_data).hexdigest()
        await self._storage.put(self._bucket_name(bucket), key, sanitised_data, mime_type)
        row = await self._repository.create(
            bucket=bucket,
            object_key=key,
            owner_user_id=owner_user_id,
            mime_type=mime_type,
            byte_size=len(sanitised_data),
            sha256=digest,
            original_name=original_name,
            scan_status=ScanStatus.SCAN_UNAVAILABLE,
        )
        await self._audit.record(
            AuditAction.DOCUMENT_UPLOADED,
            actor_type=ActorType.USER,
            actor_id=actor_id,
            target_type="stored_file",
            target_id=row.id,
            request_id=request_id,
            metadata={"bucket": bucket.value, "mimeType": mime_type, "byteSize": row.byte_size},
        )
        url = None
        if bucket is StorageBucket.PUBLIC_MEDIA:
            url = self._storage.public_url(self._bucket_name(bucket), key)
        return _view(row, url)

    async def issue_download_url(
        self,
        file_id: UUID,
        *,
        actor_id: UUID,
        request_id: str | None,
    ) -> SignedDownload:
        row = await self._require(file_id)
        if row.purged_at is not None or row.bucket is not StorageBucket.PRIVATE_DOCUMENTS:
            raise NotFoundError("Document not found.")
        ttl = self._settings.uploads_signed_url_ttl_seconds
        url = await self._storage.presigned_get(
            self._bucket_name(row.bucket),
            row.object_key,
            ttl_seconds=ttl,
            filename=row.original_name,
        )
        await self._audit.record(
            AuditAction.DOCUMENT_VIEWED,
            actor_type=ActorType.ADMIN,
            actor_id=actor_id,
            target_type="stored_file",
            target_id=row.id,
            request_id=request_id,
            metadata={"ttlSeconds": ttl},
        )
        return SignedDownload(url=url, expires_in_seconds=ttl)

    async def schedule_purge(self, file_ids: list[UUID], *, after: datetime) -> None:
        for file_id in file_ids:
            row = await self._repository.get(file_id)
            if row is not None and row.purged_at is None:
                row.purge_after = after

    async def purge_due(self, *, now: datetime | None = None) -> int:
        """Delete objects whose retention window has elapsed (BR-VER-06)."""
        moment = now or datetime.now(UTC)
        due = await self._repository.list_due_for_purge(moment)
        purged = 0
        for row in due:
            await self._storage.delete(self._bucket_name(row.bucket), row.object_key)
            row.purged_at = moment
            await self._audit.record(
                AuditAction.DOCUMENT_PURGED,
                actor_type=ActorType.SYSTEM,
                target_type="stored_file",
                target_id=row.id,
                metadata={"objectKey": row.object_key},
            )
            purged += 1
        return purged

    def retention_deadline(self) -> datetime:
        days = self._settings.verification_document_retention_days
        return datetime.now(UTC) + timedelta(days=days)

    async def _require(self, file_id: UUID) -> StoredFile:
        row = await self._repository.get(file_id)
        if row is None:
            raise NotFoundError("Document not found.")
        return row
