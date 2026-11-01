"""Admin FastAPI wiring."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz.ports import get_session_revoker
from app.core.database import get_db_session
from app.core.events import event_publisher_for
from app.core.request_id import get_request_id
from app.modules.admin.repository import AdminRepository
from app.modules.admin.service import AdminService
from app.modules.audit.service import AuditLogWriter


def get_admin_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminService:
    return AdminService(
        AdminRepository(db),
        audit=AuditLogWriter(db),
        events=event_publisher_for(request, db),
        revoker=get_session_revoker(request),
    )


AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]


def request_id_of(request: Request) -> str | None:
    return get_request_id(request)
