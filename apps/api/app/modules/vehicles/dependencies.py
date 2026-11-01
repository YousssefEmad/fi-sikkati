"""FastAPI wiring for vehicles."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.events import event_publisher_for
from app.modules.files.dependencies import FileServiceDep
from app.modules.vehicles.repository import VehicleRepository
from app.modules.vehicles.service import VehicleService


def get_vehicle_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    files: FileServiceDep,
) -> VehicleService:
    return VehicleService(
        VehicleRepository(db),
        files,
        settings,
        events=event_publisher_for(request, db),
    )


VehicleServiceDep = Annotated[VehicleService, Depends(get_vehicle_service)]
