"""Mapbox Search + Directions (OD-005). Used only when ``MAPBOX_ACCESS_TOKEN`` is set."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.core.config import Settings
from app.core.errors import MapProviderUnavailableError
from app.modules.maps.ports import GeoPoint, RouteResult

log = structlog.get_logger("app.maps.mapbox")

_GEOCODE = "https://api.mapbox.com/search/geocode/v6/forward"
_REVERSE = "https://api.mapbox.com/search/geocode/v6/reverse"
_DIRECTIONS = "https://api.mapbox.com/directions/v5/mapbox/driving"
MIN_QUERY_LEN = 2
MIN_ROUTE_STOPS = 2


class MapboxMapProvider:
    provider_name = "mapbox"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        token = settings.mapbox_access_token
        if token is None:
            msg = "MAPBOX_ACCESS_TOKEN is required for MapboxMapProvider"
            raise ValueError(msg)
        self._token = token.get_secret_value()
        self._client = client or httpx.AsyncClient(timeout=10.0)

    async def autocomplete(self, query: str, *, locale: str) -> tuple[GeoPoint, ...]:
        if len(query.strip()) < MIN_QUERY_LEN:
            return ()
        payload = await self._get(
            _GEOCODE,
            {
                "q": query.strip(),
                "language": "ar" if locale.startswith("ar") else "en",
                "country": "eg",
                "limit": "8",
                "access_token": self._token,
            },
        )
        return tuple(
            point
            for item in payload.get("features", [])
            if (point := _feature_point(item)) is not None
        )

    async def geocode(self, query: str, *, locale: str) -> GeoPoint | None:
        hits = await self.autocomplete(query, locale=locale)
        return hits[0] if hits else None

    async def reverse_geocode(self, lat: float, lng: float, *, locale: str) -> GeoPoint | None:
        payload = await self._get(
            _REVERSE,
            {
                "longitude": str(lng),
                "latitude": str(lat),
                "language": "ar" if locale.startswith("ar") else "en",
                "limit": "1",
                "access_token": self._token,
            },
        )
        features = payload.get("features", [])
        if not features:
            return None
        return _feature_point(features[0])

    async def route(self, stops: tuple[GeoPoint, ...]) -> RouteResult:
        if len(stops) < MIN_ROUTE_STOPS:
            msg = "A route needs at least origin and destination"
            raise ValueError(msg)
        path = ";".join(f"{stop.lng},{stop.lat}" for stop in stops)
        payload = await self._get(
            f"{_DIRECTIONS}/{path}",
            {
                "geometries": "geojson",
                "overview": "full",
                "access_token": self._token,
            },
        )
        routes = payload.get("routes") or []
        if not routes:
            raise MapProviderUnavailableError("Mapbox returned no driving route.")
        route = routes[0]
        geometry = route.get("geometry") or {}
        coordinates = tuple(
            (float(pair[0]), float(pair[1])) for pair in geometry.get("coordinates", [])
        )
        if len(coordinates) < MIN_ROUTE_STOPS:
            raise MapProviderUnavailableError("Mapbox returned an empty geometry.")
        return RouteResult(
            coordinates=coordinates,
            distance_m=round(float(route.get("distance", 0))),
            duration_s=round(float(route.get("duration", 0))),
            provider=self.provider_name,
            provider_ref=str(payload.get("uuid") or "directions"),
        )

    async def _get(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("mapbox_http_error", error=type(exc).__name__)
            raise MapProviderUnavailableError("Mapbox request failed.") from exc
        payload = response.json()
        if not isinstance(payload, dict):
            raise MapProviderUnavailableError("Mapbox returned an unexpected payload.")
        return payload


def _feature_point(feature: object) -> GeoPoint | None:
    if not isinstance(feature, dict):
        return None
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates") if isinstance(geometry, dict) else None
    properties_raw = feature.get("properties")
    properties = properties_raw if isinstance(properties_raw, dict) else {}
    if not isinstance(coords, list) or len(coords) < MIN_ROUTE_STOPS:
        return None
    label = str(properties.get("full_address") or properties.get("name") or feature.get("id") or "")
    return GeoPoint(lat=float(coords[1]), lng=float(coords[0]), label=label)
