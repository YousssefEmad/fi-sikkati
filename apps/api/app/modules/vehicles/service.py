"""Vehicle registry rules (BR-VEH-01, FR-DRV-03/04/06)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.core.config import Settings
from app.core.errors import (
    ConflictError,
    InvalidTransitionError,
    NotFoundError,
    ValidationAppError,
)
from app.core.events import EventPublisher, NoopEventPublisher, ReviewRequested
from app.modules.files.service import FileService, StoredFileView
from app.modules.vehicles.models import (
    REQUIRED_VEHICLE_DOCUMENT_TYPES,
    ReviewStatus,
    Vehicle,
    VehicleDocument,
    VehicleDocumentType,
    VehicleStatus,
    VehicleType,
)
from app.modules.vehicles.repository import VehicleRepository

MIN_VEHICLE_YEAR = 1980
MIN_PLATE_LENGTH = 3
MIN_REJECTION_REASON_LENGTH = 3


@dataclass(frozen=True, slots=True)
class VehicleDocumentView:
    id: UUID
    document_type: VehicleDocumentType
    file_id: UUID
    original_name: str
    mime_type: str
    byte_size: int
    status: ReviewStatus
    uploaded_at: datetime


@dataclass(frozen=True, slots=True)
class VehicleView:
    id: UUID
    owner_user_id: UUID
    make: str
    model: str
    year: int
    color: str
    vehicle_type: VehicleType
    seat_capacity: int
    plate_number: str
    status: VehicleStatus
    verification_status: ReviewStatus
    documents: tuple[VehicleDocumentView, ...]


def normalise_plate(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def _document_view(document: VehicleDocument, file: StoredFileView) -> VehicleDocumentView:
    return VehicleDocumentView(
        id=document.id,
        document_type=document.document_type,
        file_id=document.file_id,
        original_name=file.original_name,
        mime_type=file.mime_type,
        byte_size=file.byte_size,
        status=document.status,
        uploaded_at=document.created_at,
    )


class VehicleService:
    def __init__(
        self,
        repository: VehicleRepository,
        files: FileService,
        settings: Settings,
        *,
        events: EventPublisher | None = None,
    ) -> None:
        self._repository = repository
        self._files = files
        self._settings = settings
        self._events = events or NoopEventPublisher()

    async def list_mine(self, owner_user_id: UUID) -> list[VehicleView]:
        return [
            await self._to_view(vehicle)
            for vehicle in await self._repository.list_for_owner(owner_user_id)
        ]

    async def get_mine(self, owner_user_id: UUID, vehicle_id: UUID) -> VehicleView:
        vehicle = await self._owned(owner_user_id, vehicle_id)
        return await self._to_view(vehicle)

    async def get(self, vehicle_id: UUID) -> VehicleView:
        vehicle = await self._repository.get(vehicle_id)
        if vehicle is None:
            raise NotFoundError("Vehicle not found.")
        return await self._to_view(vehicle)

    async def create(
        self,
        owner_user_id: UUID,
        *,
        make: str,
        model: str,
        year: int,
        color: str,
        vehicle_type: VehicleType,
        seat_capacity: int,
        plate_number: str,
    ) -> VehicleView:
        current_year = datetime.now(UTC).year
        if year < MIN_VEHICLE_YEAR or year > current_year + 1:
            raise ValidationAppError("Vehicle year is outside the allowed range.")
        if (
            await self._repository.count_active_for_owner(owner_user_id)
            >= self._settings.vehicles_max_per_driver
        ):
            raise ConflictError(
                f"You can register at most {self._settings.vehicles_max_per_driver} vehicles.",
                code="VEHICLE_LIMIT",
            )
        plate = normalise_plate(plate_number)
        if len(plate) < MIN_PLATE_LENGTH:
            raise ValidationAppError("Licence plate is too short.")
        vehicle = await self._repository.create(
            owner_user_id=owner_user_id,
            make=make.strip(),
            model=model.strip(),
            year=year,
            color=color.strip(),
            vehicle_type=vehicle_type,
            seat_capacity=seat_capacity,
            plate_number=plate,
        )
        await self._events.publish(
            ReviewRequested(
                kind="VEHICLE",
                subject_user_id=owner_user_id,
                vehicle_id=vehicle.id,
            )
        )
        return await self._to_view(vehicle)

    async def update(
        self,
        owner_user_id: UUID,
        vehicle_id: UUID,
        *,
        make: str | None = None,
        model: str | None = None,
        year: int | None = None,
        color: str | None = None,
        vehicle_type: VehicleType | None = None,
        seat_capacity: int | None = None,
        plate_number: str | None = None,
    ) -> VehicleView:
        vehicle = await self._owned(owner_user_id, vehicle_id)
        if vehicle.verification_status is ReviewStatus.APPROVED:
            raise InvalidTransitionError(
                "An approved vehicle cannot be edited. Deactivate it and add a new one."
            )
        if make is not None:
            vehicle.make = make.strip()
        if model is not None:
            vehicle.model = model.strip()
        if year is not None:
            current_year = datetime.now(UTC).year
            if year < MIN_VEHICLE_YEAR or year > current_year + 1:
                raise ValidationAppError("Vehicle year is outside the allowed range.")
            vehicle.year = year
        if color is not None:
            vehicle.color = color.strip()
        if vehicle_type is not None:
            vehicle.vehicle_type = vehicle_type
        if seat_capacity is not None:
            vehicle.seat_capacity = seat_capacity
        if plate_number is not None:
            plate = normalise_plate(plate_number)
            if len(plate) < MIN_PLATE_LENGTH:
                raise ValidationAppError("Licence plate is too short.")
            vehicle.plate_number = plate
        return await self._to_view(vehicle)

    async def deactivate(self, owner_user_id: UUID, vehicle_id: UUID) -> VehicleView:
        vehicle = await self._owned(owner_user_id, vehicle_id)
        vehicle.status = VehicleStatus.INACTIVE
        return await self._to_view(vehicle)

    async def upload_document(
        self,
        owner_user_id: UUID,
        vehicle_id: UUID,
        *,
        document_type: VehicleDocumentType,
        data: bytes,
        filename: str | None,
        request_id: str | None,
    ) -> VehicleView:
        vehicle = await self._owned(owner_user_id, vehicle_id)
        if vehicle.verification_status is ReviewStatus.APPROVED:
            raise InvalidTransitionError("Documents for an approved vehicle cannot be replaced.")
        stored = await self._files.store_private_document(
            owner_user_id=owner_user_id,
            data=data,
            filename=filename,
            images_only=document_type is VehicleDocumentType.VEHICLE_PHOTO,
            actor_id=owner_user_id,
            request_id=request_id,
        )
        await self._repository.upsert_document(vehicle, document_type, stored.id)
        if vehicle.verification_status is ReviewStatus.REJECTED:
            vehicle.verification_status = ReviewStatus.PENDING
        return await self._to_view(vehicle)

    def has_required_documents(self, vehicle: Vehicle) -> bool:
        present = {doc.document_type for doc in vehicle.documents}
        return present >= REQUIRED_VEHICLE_DOCUMENT_TYPES

    async def require_eligible_for_driver(self, owner_user_id: UUID, vehicle_id: UUID) -> Vehicle:
        vehicle = await self._owned(owner_user_id, vehicle_id)
        if vehicle.status is not VehicleStatus.ACTIVE:
            raise InvalidTransitionError("That vehicle is not active.")
        if not self.has_required_documents(vehicle):
            raise InvalidTransitionError(
                "Upload the vehicle registration front and back before applying."
            )
        return vehicle

    async def apply_review(
        self,
        vehicle_id: UUID,
        *,
        approved: bool,
        reviewer_id: UUID,
        reason: str | None,
    ) -> VehicleView:
        vehicle = await self._repository.get(vehicle_id)
        if vehicle is None:
            raise NotFoundError("Vehicle not found.")
        if vehicle.verification_status is not ReviewStatus.PENDING:
            raise InvalidTransitionError("This vehicle is not waiting for review.")
        if not approved and not (reason and len(reason.strip()) >= MIN_REJECTION_REASON_LENGTH):
            raise ValidationAppError("A rejection reason is required.")
        status = ReviewStatus.APPROVED if approved else ReviewStatus.REJECTED
        now = datetime.now(UTC)
        await self._repository.apply_review(
            vehicle,
            status=status,
            reviewer_id=reviewer_id,
            reviewed_at=now,
            reason=reason.strip() if reason else None,
        )
        file_ids = [doc.file_id for doc in vehicle.documents]
        await self._files.schedule_purge(file_ids, after=self._files.retention_deadline())
        return await self._to_view(vehicle)

    async def list_pending(self, *, page: int, page_size: int) -> tuple[list[VehicleView], int]:
        offset = (page - 1) * page_size
        rows, total = await self._repository.list_pending(offset=offset, limit=page_size)
        return [await self._to_view(row) for row in rows], total

    async def admin_deactivate(self, vehicle_id: UUID) -> VehicleView:
        vehicle = await self._repository.get(vehicle_id)
        if vehicle is None:
            raise NotFoundError("Vehicle not found.")
        vehicle.status = VehicleStatus.INACTIVE
        return await self._to_view(vehicle)

    async def _owned(self, owner_user_id: UUID, vehicle_id: UUID) -> Vehicle:
        vehicle = await self._repository.get(vehicle_id)
        if vehicle is None or vehicle.owner_user_id != owner_user_id:
            raise NotFoundError("Vehicle not found.")
        return vehicle

    async def _to_view(self, vehicle: Vehicle) -> VehicleView:
        documents: list[VehicleDocumentView] = []
        for document in vehicle.documents:
            stored = await self._files.get(document.file_id)
            documents.append(_document_view(document, stored))
        return VehicleView(
            id=vehicle.id,
            owner_user_id=vehicle.owner_user_id,
            make=vehicle.make,
            model=vehicle.model,
            year=vehicle.year,
            color=vehicle.color,
            vehicle_type=vehicle.vehicle_type,
            seat_capacity=vehicle.seat_capacity,
            plate_number=vehicle.plate_number,
            status=vehicle.status,
            verification_status=vehicle.verification_status,
            documents=tuple(documents),
        )
