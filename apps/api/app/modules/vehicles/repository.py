"""SQL for vehicles and their documents."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.ids import uuid7
from app.modules.vehicles.models import (
    ReviewStatus,
    Vehicle,
    VehicleDocument,
    VehicleDocumentType,
    VehicleStatus,
    VehicleType,
)


class VehicleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, vehicle_id: UUID) -> Vehicle | None:
        result = await self._db.execute(
            select(Vehicle).options(selectinload(Vehicle.documents)).where(Vehicle.id == vehicle_id)
        )
        return result.scalar_one_or_none()

    async def list_for_owner(self, owner_user_id: UUID) -> list[Vehicle]:
        result = await self._db.execute(
            select(Vehicle)
            .options(selectinload(Vehicle.documents))
            .where(Vehicle.owner_user_id == owner_user_id)
            .order_by(Vehicle.created_at.desc())
        )
        return list(result.scalars())

    async def count_active_for_owner(self, owner_user_id: UUID) -> int:
        result = await self._db.execute(
            select(func.count())
            .select_from(Vehicle)
            .where(
                Vehicle.owner_user_id == owner_user_id,
                Vehicle.status == VehicleStatus.ACTIVE,
            )
        )
        return int(result.scalar_one())

    async def create(
        self,
        *,
        owner_user_id: UUID,
        make: str,
        model: str,
        year: int,
        color: str,
        vehicle_type: VehicleType,
        seat_capacity: int,
        plate_number: str,
    ) -> Vehicle:
        vehicle = Vehicle(
            id=uuid7(),
            owner_user_id=owner_user_id,
            make=make,
            model=model,
            year=year,
            color=color,
            vehicle_type=vehicle_type,
            seat_capacity=seat_capacity,
            plate_number=plate_number,
        )
        vehicle.documents = []
        self._db.add(vehicle)
        await self._db.flush()
        return vehicle

    async def upsert_document(
        self, vehicle: Vehicle, document_type: VehicleDocumentType, file_id: UUID
    ) -> VehicleDocument:
        existing = next(
            (doc for doc in vehicle.documents if doc.document_type is document_type), None
        )
        if existing is None:
            existing = VehicleDocument(
                id=uuid7(),
                vehicle_id=vehicle.id,
                document_type=document_type,
                file_id=file_id,
                status=ReviewStatus.PENDING,
            )
            self._db.add(existing)
            vehicle.documents.append(existing)
        else:
            existing.file_id = file_id
            existing.status = ReviewStatus.PENDING
            existing.reviewed_by = None
            existing.reviewed_at = None
            existing.rejection_reason = None
        await self._db.flush()
        return existing

    async def list_pending(self, *, offset: int, limit: int) -> tuple[list[Vehicle], int]:
        filters = (Vehicle.verification_status == ReviewStatus.PENDING,)
        total = int(
            (
                await self._db.execute(select(func.count()).select_from(Vehicle).where(*filters))
            ).scalar_one()
        )
        result = await self._db.execute(
            select(Vehicle)
            .options(selectinload(Vehicle.documents))
            .where(*filters)
            .order_by(Vehicle.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars()), total

    async def apply_review(
        self,
        vehicle: Vehicle,
        *,
        status: ReviewStatus,
        reviewer_id: UUID,
        reviewed_at: datetime,
        reason: str | None,
    ) -> None:
        vehicle.verification_status = status
        for document in vehicle.documents:
            document.status = status
            document.reviewed_by = reviewer_id
            document.reviewed_at = reviewed_at
            document.rejection_reason = reason if status is ReviewStatus.REJECTED else None
        await self._db.flush()
