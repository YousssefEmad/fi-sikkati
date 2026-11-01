"""HTTP shapes for map helpers."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.core.schemas import ApiModel


class MapPoint(ApiModel):
    lat: float
    lng: float
    label: str


class AutocompleteResponse(ApiModel):
    items: list[MapPoint]


class GeocodeResponse(ApiModel):
    point: MapPoint | None


class RouteStopInput(ApiModel):
    lat: Annotated[float, Field(ge=-90, le=90)]
    lng: Annotated[float, Field(ge=-180, le=180)]
    label: Annotated[str, Field(min_length=1, max_length=200)]


class RoutePreviewRequest(ApiModel):
    stops: Annotated[list[RouteStopInput], Field(min_length=2, max_length=8)]


class RoutePreviewResponse(ApiModel):
    coordinates: list[list[float]]
    distance_m: int
    duration_s: int
    provider: str
