"""Identity and driver verification (BR-VER-01..07)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from app.core.authz.permissions import Role
from app.core.config import Settings
from app.core.email import EmailSender
from app.core.errors import (
    EmailNotVerifiedError,
    InvalidTransitionError,
    NotFoundError,
    ValidationAppError,
)
from app.core.events import (
    EventPublisher,
    NoopEventPublisher,
    ReviewRequested,
    VerificationStatusChanged,
)
from app.modules.audit.models import ActorType, AuditAction
from app.modules.audit.service import AuditLogWriter
from app.modules.files.service import FileService, StoredFileView
from app.modules.users.models import IdentityVerificationStatus
from app.modules.users.service import UserService
from app.modules.vehicles.service import VehicleService
from app.modules.verification.emails import driver_decision_email, identity_decision_email
from app.modules.verification.models import (
    REQUIRED_IDENTITY_DOCUMENT_TYPES,
    DriverVerification,
    DriverVerificationStatus,
    IdentityDocument,
    IdentityDocumentType,
    ReviewStatus,
)
from app.modules.verification.repository import VerificationRepository

MIN_REJECTION_REASON_LENGTH = 3


@dataclass(frozen=True, slots=True)
class IdentityDocumentView:
    id: UUID
    document_type: IdentityDocumentType
    file_id: UUID
    original_name: str
    mime_type: str
    byte_size: int
    status: ReviewStatus
    uploaded_at: datetime


@dataclass(frozen=True, slots=True)
class DriverStatusView:
    status: DriverVerificationStatus | None
    licence_expires_on: date | None
    licence_file_id: UUID | None
    licence_original_name: str | None
    vehicle_id: UUID | None
    rejection_reason: str | None
    submitted_at: datetime | None


@dataclass(frozen=True, slots=True)
class VerificationStatusView:
    identity_status: IdentityVerificationStatus
    identity_documents: tuple[IdentityDocumentView, ...]
    identity_rejection_reason: str | None
    review_sla_hours: int
    driver: DriverStatusView


@dataclass(frozen=True, slots=True)
class AdminIdentityItem:
    user_id: UUID
    display_name: str
    email: str
    submitted_at: datetime
    document_count: int


@dataclass(frozen=True, slots=True)
class AdminDriverItem:
    user_id: UUID
    verification_id: UUID
    display_name: str
    email: str
    submitted_at: datetime
    vehicle_id: UUID
    licence_expires_on: date


class VerificationService:
    def __init__(
        self,
        repository: VerificationRepository,
        users: UserService,
        vehicles: VehicleService,
        files: FileService,
        settings: Settings,
        audit: AuditLogWriter,
        email: EmailSender,
        events: EventPublisher | None = None,
    ) -> None:
        self._repository = repository
        self._users = users
        self._vehicles = vehicles
        self._files = files
        self._settings = settings
        self._audit = audit
        self._email = email
        self._events = events or NoopEventPublisher()

    async def get_status(self, user_id: UUID) -> VerificationStatusView:
        account = await self._users.get_account(user_id)
        latest = await self._repository.latest_identity_by_type(user_id)
        documents = []
        rejection = None
        for document in latest.values():
            stored = await self._files.get(document.file_id)
            documents.append(_identity_view(document, stored))
            if document.status is ReviewStatus.REJECTED and document.rejection_reason:
                rejection = document.rejection_reason
        driver = await self._repository.latest_driver(user_id)
        return VerificationStatusView(
            identity_status=account.identity_verification_status,
            identity_documents=tuple(documents),
            identity_rejection_reason=rejection,
            review_sla_hours=self._settings.verification_review_sla_hours,
            driver=await self._driver_view(driver),
        )

    async def upload_identity_document(
        self,
        user_id: UUID,
        *,
        document_type: IdentityDocumentType,
        data: bytes,
        filename: str | None,
        request_id: str | None,
    ) -> VerificationStatusView:
        account = await self._users.get_account(user_id)
        if account.identity_verification_status in {
            IdentityVerificationStatus.PENDING,
            IdentityVerificationStatus.APPROVED,
        }:
            raise InvalidTransitionError(
                "Identity documents cannot be changed in the current state."
            )
        stored = await self._files.store_private_document(
            owner_user_id=user_id,
            data=data,
            filename=filename,
            images_only=document_type is IdentityDocumentType.SELFIE,
            actor_id=user_id,
            request_id=request_id,
        )
        await self._repository.upsert_identity_document(user_id, document_type, stored.id)
        return await self.get_status(user_id)

    async def submit_identity(
        self, user_id: UUID, *, request_id: str | None
    ) -> VerificationStatusView:
        account = await self._users.get_account(user_id)
        if not account.email_verified:
            raise EmailNotVerifiedError("Confirm your email before submitting identity documents.")
        if account.identity_verification_status not in {
            IdentityVerificationStatus.NOT_SUBMITTED,
            IdentityVerificationStatus.REJECTED,
        }:
            raise InvalidTransitionError(
                "Identity verification cannot be submitted in the current state."
            )
        latest = await self._repository.latest_identity_by_type(user_id)
        missing = REQUIRED_IDENTITY_DOCUMENT_TYPES - set(latest)
        if missing:
            raise InvalidTransitionError("Upload the national ID front, back and a selfie first.")
        user = await self._users.require_user(user_id)
        user.identity_verification_status = IdentityVerificationStatus.PENDING
        await self._audit.record(
            AuditAction.VERIFICATION_SUBMITTED,
            actor_type=ActorType.USER,
            actor_id=user_id,
            target_type="identity_verification",
            target_id=user_id,
            request_id=request_id,
            metadata={"kind": "identity"},
        )
        await self._events.publish(ReviewRequested(kind="IDENTITY", subject_user_id=user_id))
        return await self.get_status(user_id)

    async def upload_licence(
        self,
        user_id: UUID,
        *,
        data: bytes,
        filename: str | None,
        request_id: str | None,
    ) -> StoredFileView:
        account = await self._users.get_account(user_id)
        if not account.email_verified:
            raise EmailNotVerifiedError("Confirm your email before applying to drive.")
        active = await self._repository.get_active_driver(user_id)
        if active is not None and active.status is DriverVerificationStatus.PENDING:
            raise InvalidTransitionError("A driver application is already under review.")
        if account.identity_verification_status not in {
            IdentityVerificationStatus.APPROVED,
            IdentityVerificationStatus.PENDING,
        }:
            raise InvalidTransitionError("Verify your identity before applying to drive.")
        return await self._files.store_private_document(
            owner_user_id=user_id,
            data=data,
            filename=filename,
            actor_id=user_id,
            request_id=request_id,
        )

    async def submit_driver(
        self,
        user_id: UUID,
        *,
        vehicle_id: UUID,
        licence_expires_on: date,
        licence_file_id: UUID,
        request_id: str | None,
    ) -> VerificationStatusView:
        account = await self._users.get_account(user_id)
        if not account.email_verified:
            raise EmailNotVerifiedError("Confirm your email before applying to drive.")
        if account.identity_verification_status not in {
            IdentityVerificationStatus.APPROVED,
            IdentityVerificationStatus.PENDING,
        }:
            raise InvalidTransitionError("Verify your identity before applying to drive.")
        if licence_expires_on <= datetime.now(UTC).date():
            raise ValidationAppError("The driving licence must still be valid.")
        active = await self._repository.get_active_driver(user_id)
        if active is not None:
            raise InvalidTransitionError("A driver application is already pending or approved.")
        stored = await self._files.get(licence_file_id)
        if stored.owner_user_id != user_id or stored.purged_at is not None:
            raise NotFoundError("Licence file not found.")
        vehicle = await self._vehicles.require_eligible_for_driver(user_id, vehicle_id)
        row = await self._repository.create_driver(
            user_id=user_id,
            licence_file_id=licence_file_id,
            licence_expires_on=licence_expires_on,
            vehicle_id=vehicle.id,
        )
        await self._audit.record(
            AuditAction.VERIFICATION_SUBMITTED,
            actor_type=ActorType.USER,
            actor_id=user_id,
            target_type="driver_verification",
            target_id=row.id,
            request_id=request_id,
            metadata={"vehicleId": str(vehicle_id)},
        )
        await self._events.publish(ReviewRequested(kind="DRIVER", subject_user_id=user_id))
        return await self.get_status(user_id)

    async def approve_identity(
        self, user_id: UUID, *, reviewer_id: UUID, request_id: str | None
    ) -> VerificationStatusView:
        account = await self._users.get_account(user_id)
        if account.identity_verification_status is not IdentityVerificationStatus.PENDING:
            raise InvalidTransitionError("This identity application is not waiting for review.")
        latest = list((await self._repository.latest_identity_by_type(user_id)).values())
        now = datetime.now(UTC)
        await self._repository.apply_identity_review(
            latest,
            status=ReviewStatus.APPROVED,
            reviewer_id=reviewer_id,
            reviewed_at=now,
            reason=None,
        )
        user = await self._users.require_user(user_id)
        user.identity_verification_status = IdentityVerificationStatus.APPROVED
        await self._files.schedule_purge(
            [doc.file_id for doc in latest], after=self._files.retention_deadline()
        )
        await self._audit.record(
            AuditAction.VERIFICATION_APPROVED,
            actor_type=ActorType.ADMIN,
            actor_id=reviewer_id,
            target_type="identity_verification",
            target_id=user_id,
            request_id=request_id,
            metadata={"kind": "identity"},
        )
        await self._email.send(
            identity_decision_email(
                to=account.email,
                display_name=account.display_name,
                locale=account.locale,
                approved=True,
                reason=None,
                link=f"{self._settings.public_web_url}me/verification",
            )
        )
        await self._events.publish(
            VerificationStatusChanged(user_id=user_id, kind="IDENTITY", status="APPROVED")
        )
        return await self.get_status(user_id)

    async def reject_identity(
        self, user_id: UUID, *, reviewer_id: UUID, reason: str, request_id: str | None
    ) -> VerificationStatusView:
        if len(reason.strip()) < MIN_REJECTION_REASON_LENGTH:
            raise ValidationAppError("A rejection reason is required.")
        account = await self._users.get_account(user_id)
        if account.identity_verification_status is not IdentityVerificationStatus.PENDING:
            raise InvalidTransitionError("This identity application is not waiting for review.")
        latest = list((await self._repository.latest_identity_by_type(user_id)).values())
        now = datetime.now(UTC)
        trimmed = reason.strip()
        await self._repository.apply_identity_review(
            latest,
            status=ReviewStatus.REJECTED,
            reviewer_id=reviewer_id,
            reviewed_at=now,
            reason=trimmed,
        )
        user = await self._users.require_user(user_id)
        user.identity_verification_status = IdentityVerificationStatus.REJECTED
        await self._files.schedule_purge(
            [doc.file_id for doc in latest], after=self._files.retention_deadline()
        )
        await self._audit.record(
            AuditAction.VERIFICATION_REJECTED,
            actor_type=ActorType.ADMIN,
            actor_id=reviewer_id,
            target_type="identity_verification",
            target_id=user_id,
            request_id=request_id,
            metadata={"kind": "identity"},
        )
        await self._email.send(
            identity_decision_email(
                to=account.email,
                display_name=account.display_name,
                locale=account.locale,
                approved=False,
                reason=trimmed,
                link=f"{self._settings.public_web_url}me/verification",
            )
        )
        await self._events.publish(
            VerificationStatusChanged(user_id=user_id, kind="IDENTITY", status="REJECTED")
        )
        return await self.get_status(user_id)

    async def approve_driver(
        self, user_id: UUID, *, reviewer_id: UUID, request_id: str | None
    ) -> VerificationStatusView:
        account = await self._users.get_account(user_id)
        if account.identity_verification_status is IdentityVerificationStatus.PENDING:
            await self.approve_identity(user_id, reviewer_id=reviewer_id, request_id=request_id)
        row = await self._repository.get_active_driver(user_id)
        if row is None or row.status is not DriverVerificationStatus.PENDING:
            raise InvalidTransitionError("This driver application is not waiting for review.")
        now = datetime.now(UTC)
        row.status = DriverVerificationStatus.APPROVED
        row.reviewed_by = reviewer_id
        row.reviewed_at = now
        await self._users.grant_role(user_id, Role.DRIVER, granted_by=reviewer_id)
        await self._vehicles.apply_review(
            row.vehicle_id, approved=True, reviewer_id=reviewer_id, reason=None
        )
        await self._files.schedule_purge(
            [row.licence_file_id], after=self._files.retention_deadline()
        )
        await self._audit.record(
            AuditAction.VERIFICATION_APPROVED,
            actor_type=ActorType.ADMIN,
            actor_id=reviewer_id,
            target_type="driver_verification",
            target_id=row.id,
            request_id=request_id,
            metadata={"kind": "driver"},
        )
        await self._audit.record(
            AuditAction.ROLE_GRANTED,
            actor_type=ActorType.ADMIN,
            actor_id=reviewer_id,
            target_type="user",
            target_id=user_id,
            request_id=request_id,
            metadata={"role": Role.DRIVER.value},
        )
        account = await self._users.get_account(user_id)
        await self._email.send(
            driver_decision_email(
                to=account.email,
                display_name=account.display_name,
                locale=account.locale,
                approved=True,
                reason=None,
                link=f"{self._settings.public_web_url}drive",
            )
        )
        await self._events.publish(
            VerificationStatusChanged(user_id=user_id, kind="DRIVER", status="APPROVED")
        )
        return await self.get_status(user_id)

    async def approve_vehicle_registration(
        self, user_id: UUID, vehicle_id: UUID, *, reviewer_id: UUID, request_id: str | None
    ) -> VerificationStatusView:
        """Approve a saved vehicle and let that person publish trips."""
        vehicle = await self._vehicles.get(vehicle_id)
        if vehicle.owner_user_id != user_id:
            raise NotFoundError("Vehicle not found.")
        account = await self._users.get_account(user_id)
        if account.identity_verification_status is IdentityVerificationStatus.PENDING:
            await self.approve_identity(user_id, reviewer_id=reviewer_id, request_id=request_id)
        elif account.identity_verification_status is not IdentityVerificationStatus.APPROVED:
            raise InvalidTransitionError(
                "Identity documents must be submitted before this driver can be approved."
            )
        await self._vehicles.apply_review(
            vehicle_id, approved=True, reviewer_id=reviewer_id, reason=None
        )
        await self._users.grant_role(user_id, Role.DRIVER, granted_by=reviewer_id)
        await self._audit.record(
            AuditAction.ROLE_GRANTED,
            actor_type=ActorType.ADMIN,
            actor_id=reviewer_id,
            target_type="user",
            target_id=user_id,
            request_id=request_id,
            metadata={"role": Role.DRIVER.value, "vehicleId": str(vehicle_id)},
        )
        account = await self._users.get_account(user_id)
        await self._email.send(
            driver_decision_email(
                to=account.email,
                display_name=account.display_name,
                locale=account.locale,
                approved=True,
                reason=None,
                link=f"{self._settings.public_web_url}drive",
            )
        )
        await self._events.publish(
            VerificationStatusChanged(user_id=user_id, kind="DRIVER", status="APPROVED")
        )
        return await self.get_status(user_id)

    async def reject_driver(
        self, user_id: UUID, *, reviewer_id: UUID, reason: str, request_id: str | None
    ) -> VerificationStatusView:
        if len(reason.strip()) < MIN_REJECTION_REASON_LENGTH:
            raise ValidationAppError("A rejection reason is required.")
        row = await self._repository.get_active_driver(user_id)
        if row is None or row.status is not DriverVerificationStatus.PENDING:
            raise InvalidTransitionError("This driver application is not waiting for review.")
        now = datetime.now(UTC)
        trimmed = reason.strip()
        row.status = DriverVerificationStatus.REJECTED
        row.reviewed_by = reviewer_id
        row.reviewed_at = now
        row.rejection_reason = trimmed
        await self._vehicles.apply_review(
            row.vehicle_id, approved=False, reviewer_id=reviewer_id, reason=trimmed
        )
        await self._files.schedule_purge(
            [row.licence_file_id], after=self._files.retention_deadline()
        )
        await self._audit.record(
            AuditAction.VERIFICATION_REJECTED,
            actor_type=ActorType.ADMIN,
            actor_id=reviewer_id,
            target_type="driver_verification",
            target_id=row.id,
            request_id=request_id,
            metadata={"kind": "driver"},
        )
        account = await self._users.get_account(user_id)
        await self._email.send(
            driver_decision_email(
                to=account.email,
                display_name=account.display_name,
                locale=account.locale,
                approved=False,
                reason=trimmed,
                link=f"{self._settings.public_web_url}drive",
            )
        )
        await self._events.publish(
            VerificationStatusChanged(user_id=user_id, kind="DRIVER", status="REJECTED")
        )
        return await self.get_status(user_id)

    async def list_pending_identity(
        self, *, page: int, page_size: int
    ) -> tuple[list[AdminIdentityItem], int]:
        offset = (page - 1) * page_size
        users, total = await self._repository.list_pending_identity_users(
            offset=offset, limit=page_size
        )
        items: list[AdminIdentityItem] = []
        for user in users:
            latest = await self._repository.latest_identity_by_type(user.id)
            items.append(
                AdminIdentityItem(
                    user_id=user.id,
                    display_name=user.profile.display_name,
                    email=user.email,
                    submitted_at=user.updated_at,
                    document_count=len(latest),
                )
            )
        return items, total

    async def list_pending_drivers(
        self, *, page: int, page_size: int
    ) -> tuple[list[AdminDriverItem], int]:
        offset = (page - 1) * page_size
        rows, total = await self._repository.list_pending_drivers(offset=offset, limit=page_size)
        items: list[AdminDriverItem] = []
        for row in rows:
            account = await self._users.get_account(row.user_id)
            items.append(
                AdminDriverItem(
                    user_id=row.user_id,
                    verification_id=row.id,
                    display_name=account.display_name,
                    email=account.email,
                    submitted_at=row.created_at,
                    vehicle_id=row.vehicle_id,
                    licence_expires_on=row.licence_expires_on,
                )
            )
        return items, total

    async def _driver_view(self, row: DriverVerification | None) -> DriverStatusView:
        if row is None:
            return DriverStatusView(
                status=None,
                licence_expires_on=None,
                licence_file_id=None,
                licence_original_name=None,
                vehicle_id=None,
                rejection_reason=None,
                submitted_at=None,
            )
        stored = await self._files.get(row.licence_file_id)
        return DriverStatusView(
            status=row.status,
            licence_expires_on=row.licence_expires_on,
            licence_file_id=row.licence_file_id,
            licence_original_name=stored.original_name,
            vehicle_id=row.vehicle_id,
            rejection_reason=row.rejection_reason,
            submitted_at=row.created_at,
        )


def _identity_view(document: IdentityDocument, stored: StoredFileView) -> IdentityDocumentView:
    return IdentityDocumentView(
        id=document.id,
        document_type=document.document_type,
        file_id=document.file_id,
        original_name=stored.original_name,
        mime_type=stored.mime_type,
        byte_size=stored.byte_size,
        status=document.status,
        uploaded_at=document.created_at,
    )
