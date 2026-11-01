"""``MapProvider`` protocol — domain code never imports a vendor SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GeoPoint:
    lat: float
    lng: float
    label: str


@dataclass(frozen=True, slots=True)
class RouteResult:
    """WGS84 polyline as ``(lng, lat)`` pairs, plus length and duration."""

    coordinates: tuple[tuple[float, float], ...]
    distance_m: int
    duration_s: int
    provider: str
    provider_ref: str


class MapProvider(Protocol):
    async def autocomplete(self, query: str, *, locale: str) -> tuple[GeoPoint, ...]: ...

    async def geocode(self, query: str, *, locale: str) -> GeoPoint | None: ...

    async def reverse_geocode(self, lat: float, lng: float, *, locale: str) -> GeoPoint | None: ...

    async def route(self, stops: tuple[GeoPoint, ...]) -> RouteResult: ...
