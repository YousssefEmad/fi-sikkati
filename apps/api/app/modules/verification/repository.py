"""SQL for identity documents and driver applications."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import uuid7
from app.modules.users.models import IdentityVerificationStatus, User
from app.modules.verification.models import (
    DriverVerification,
    DriverVerificationStatus,
    IdentityDocument,
    IdentityDocumentType,
    ReviewStatus,
)


class VerificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_identity_documents(self, user_id: UUID) -> list[IdentityDocument]:
        result = await self._db.execute(
            select(IdentityDocument)
            .where(IdentityDocument.user_id == user_id)
            .order_by(IdentityDocument.created_at.desc())
        )
        return list(result.scalars())

    async def upsert_identity_document(
        self, user_id: UUID, document_type: IdentityDocumentType, file_id: UUID
    ) -> IdentityDocument:
        result = await self._db.execute(
            select(IdentityDocument).where(
                IdentityDocument.user_id == user_id,
                IdentityDocument.document_type == document_type,
                IdentityDocument.status != ReviewStatus.APPROVED,
            )
        )
        existing = result.scalars().first()
        if existing is None:
            existing = IdentityDocument(
                id=uuid7(),
                user_id=user_id,
                document_type=document_type,
                file_id=file_id,
                status=ReviewStatus.PENDING,
            )
            self._db.add(existing)
        else:
            existing.file_id = file_id
            existing.status = ReviewStatus.PENDING
            existing.reviewed_by = None
            existing.reviewed_at = None
            existing.rejection_reason = None
        await self._db.flush()
        return existing

    async def latest_identity_by_type(
        self, user_id: UUID
    ) -> dict[IdentityDocumentType, IdentityDocument]:
        latest: dict[IdentityDocumentType, IdentityDocument] = {}
        for document in await self.list_identity_documents(user_id):
            latest.setdefault(document.document_type, document)
        return latest

    async def apply_identity_review(
        self,
        documents: list[IdentityDocument],
        *,
        status: ReviewStatus,
        reviewer_id: UUID,
        reviewed_at: datetime,
        reason: str | None,
    ) -> None:
        for document in documents:
            if document.status is ReviewStatus.PENDING:
                document.status = status
                document.reviewed_by = reviewer_id
                document.reviewed_at = reviewed_at
                document.rejection_reason = reason if status is ReviewStatus.REJECTED else None
        await self._db.flush()

    async def get_active_driver(self, user_id: UUID) -> DriverVerification | None:
        result = await self._db.execute(
            select(DriverVerification).where(
                DriverVerification.user_id == user_id,
                DriverVerification.status.in_(
                    (DriverVerificationStatus.PENDING, DriverVerificationStatus.APPROVED)
                ),
            )
        )
        return result.scalar_one_or_none()

    async def latest_driver(self, user_id: UUID) -> DriverVerification | None:
        result = await self._db.execute(
            select(DriverVerification)
            .where(DriverVerification.user_id == user_id)
            .order_by(DriverVerification.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_driver(
        self,
        *,
        user_id: UUID,
        licence_file_id: UUID,
        licence_expires_on: date,
        vehicle_id: UUID,
    ) -> DriverVerification:
        row = DriverVerification(
            id=uuid7(),
            user_id=user_id,
            licence_file_id=licence_file_id,
            licence_expires_on=licence_expires_on,
            vehicle_id=vehicle_id,
            status=DriverVerificationStatus.PENDING,
        )
        self._db.add(row)
        await self._db.flush()
        return row

    async def get_driver(self, verification_id: UUID) -> DriverVerification | None:
        return await self._db.get(DriverVerification, verification_id)

    async def list_pending_identity_users(
        self, *, offset: int, limit: int
    ) -> tuple[list[User], int]:
        filters = (User.identity_verification_status == IdentityVerificationStatus.PENDING,)
        total = int(
            (
                await self._db.execute(select(func.count()).select_from(User).where(*filters))
            ).scalar_one()
        )
        result = await self._db.execute(
            select(User).where(*filters).order_by(User.updated_at.asc()).offset(offset).limit(limit)
        )
        return list(result.unique().scalars()), total

    async def list_pending_drivers(
        self, *, offset: int, limit: int
    ) -> tuple[list[DriverVerification], int]:
        filters = (DriverVerification.status == DriverVerificationStatus.PENDING,)
        total = int(
            (
                await self._db.execute(
                    select(func.count()).select_from(DriverVerification).where(*filters)
                )
            ).scalar_one()
        )
        result = await self._db.execute(
            select(DriverVerification)
            .where(*filters)
            .order_by(DriverVerification.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars()), total
