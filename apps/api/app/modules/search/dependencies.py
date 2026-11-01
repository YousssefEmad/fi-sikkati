"""Search FastAPI wiring."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.modules.search.service import SearchService
from app.modules.trips.repository import TripRepository


def get_search_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SearchService:
    return SearchService(TripRepository(db), settings)


SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]
