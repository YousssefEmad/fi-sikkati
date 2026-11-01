"""``/maps/*`` helpers (api.md §4.5). Geometry is never accepted from clients on trips."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.authz.dependencies import require_permission
from app.core.authz.permissions import Permission
from app.core.authz.principal import Principal
from app.modules.maps.dependencies import MapProviderDep
from app.modules.maps.ports import GeoPoint
from app.modules.maps.schemas import (
    AutocompleteResponse,
    GeocodeResponse,
    MapPoint,
    RoutePreviewRequest,
    RoutePreviewResponse,
)

router = APIRouter(prefix="/maps", tags=["maps"])


def _point(item: GeoPoint) -> MapPoint:
    return MapPoint(lat=item.lat, lng=item.lng, label=item.label)


@router.get(
    "/autocomplete",
    response_model=AutocompleteResponse,
    operation_id="maps_autocomplete",
    summary="Place autocomplete (Egypt)",
)
async def autocomplete(
    provider: MapProviderDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.MAPS_USE))],
    q: Annotated[str, Query(min_length=2, max_length=120)],
) -> AutocompleteResponse:
    del principal
    hits = await provider.autocomplete(q, locale="ar")
    return AutocompleteResponse(items=[_point(item) for item in hits])


@router.get(
    "/geocode",
    response_model=GeocodeResponse,
    operation_id="maps_geocode",
    summary="Geocode a place query",
)
async def geocode(
    provider: MapProviderDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.MAPS_USE))],
    q: Annotated[str, Query(min_length=2, max_length=200)],
) -> GeocodeResponse:
    del principal
    point = await provider.geocode(q, locale="ar")
    return GeocodeResponse(point=None if point is None else _point(point))


@router.post(
    "/route-preview",
    response_model=RoutePreviewResponse,
    operation_id="maps_route_preview",
    summary="Server-side route preview",
)
async def route_preview(
    payload: RoutePreviewRequest,
    provider: MapProviderDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.MAPS_USE))],
) -> RoutePreviewResponse:
    del principal
    stops = tuple(GeoPoint(lat=stop.lat, lng=stop.lng, label=stop.label) for stop in payload.stops)
    result = await provider.route(stops)
    return RoutePreviewResponse(
        coordinates=[list(pair) for pair in result.coordinates],
        distance_m=result.distance_m,
        duration_s=result.duration_s,
        provider=result.provider,
    )
