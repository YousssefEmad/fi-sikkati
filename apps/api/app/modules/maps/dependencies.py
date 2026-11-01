"""Maps FastAPI wiring."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.modules.maps.fake import FakeMapProvider
from app.modules.maps.ports import MapProvider


def get_map_provider(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> MapProvider:
    provider = getattr(request.app.state, "map_provider", None)
    if provider is not None:
        return provider  # type: ignore[no-any-return]
    del settings
    return FakeMapProvider()


MapProviderDep = Annotated[MapProvider, Depends(get_map_provider)]
