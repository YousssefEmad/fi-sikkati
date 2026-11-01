"""FastAPI wiring for verification."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.email import EmailSender
from app.core.events import event_publisher_for
from app.core.request_id import get_request_id
from app.modules.audit.service import AuditLogWriter
from app.modules.auth.dependencies import get_email_sender
from app.modules.files.dependencies import FileServiceDep
from app.modules.users.dependencies import UserServiceDep
from app.modules.vehicles.dependencies import VehicleServiceDep
from app.modules.verification.repository import VerificationRepository
from app.modules.verification.service import VerificationService


def get_verification_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    users: UserServiceDep,
    vehicles: VehicleServiceDep,
    files: FileServiceDep,
    email_sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> VerificationService:
    return VerificationService(
        VerificationRepository(db),
        users,
        vehicles,
        files,
        settings,
        AuditLogWriter(db),
        email_sender,
        events=event_publisher_for(request, db),
    )


VerificationServiceDep = Annotated[VerificationService, Depends(get_verification_service)]


def request_id_of(request: Request) -> str | None:
    return get_request_id(request)
