"""SQL for ``stored_files``."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import uuid7
from app.modules.files.models import ScanStatus, StorageBucket, StoredFile


class FileRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, file_id: UUID) -> StoredFile | None:
        return await self._db.get(StoredFile, file_id)

    async def create(
        self,
        *,
        bucket: StorageBucket,
        object_key: str,
        owner_user_id: UUID,
        mime_type: str,
        byte_size: int,
        sha256: str,
        original_name: str,
        scan_status: ScanStatus,
    ) -> StoredFile:
        row = StoredFile(
            id=uuid7(),
            bucket=bucket,
            object_key=object_key,
            owner_user_id=owner_user_id,
            mime_type=mime_type,
            byte_size=byte_size,
            sha256=sha256,
            original_name=original_name,
            scan_status=scan_status,
        )
        self._db.add(row)
        await self._db.flush()
        return row

    async def list_due_for_purge(self, now: datetime) -> list[StoredFile]:
        result = await self._db.execute(
            select(StoredFile).where(
                StoredFile.purge_after.is_not(None),
                StoredFile.purge_after <= now,
                StoredFile.purged_at.is_(None),
            )
        )
        return list(result.scalars())
