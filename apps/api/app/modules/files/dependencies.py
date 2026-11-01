"""FastAPI wiring for the files module."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.modules.audit.service import AuditLogWriter
from app.modules.files.ports import ObjectStorage
from app.modules.files.repository import FileRepository
from app.modules.files.service import FileService


def get_object_storage(request: Request) -> ObjectStorage:
    storage = getattr(request.app.state, "object_storage", None)
    if storage is None:  # pragma: no cover — wiring error
        msg = "ObjectStorage is not initialised on app.state"
        raise TypeError(msg)
    return storage  # type: ignore[no-any-return]


def get_file_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
) -> FileService:
    return FileService(FileRepository(db), storage, settings, AuditLogWriter(db))


FileServiceDep = Annotated[FileService, Depends(get_file_service)]
