"""WKT helpers so trip code never asks the client for geometry."""

from __future__ import annotations

from geoalchemy2.elements import WKTElement

from app.modules.maps.geo import path_length_m

MIN_LINESTRING_POINTS = 2


def point_wkt(lat: float, lng: float) -> WKTElement:
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def linestring_wkt(coordinates: tuple[tuple[float, float], ...]) -> WKTElement:
    if len(coordinates) < MIN_LINESTRING_POINTS:
        msg = "A linestring needs at least two positions"
        raise ValueError(msg)
    body = ", ".join(f"{lng} {lat}" for lng, lat in coordinates)
    return WKTElement(f"LINESTRING({body})", srid=4326)


def parse_point_wkt(wkt: str) -> tuple[float, float]:
    """Return ``(lat, lng)`` from ``POINT(lng lat)``."""
    inner = wkt.replace("POINT", "").replace("(", "").replace(")", "").strip()
    lng_s, lat_s = inner.split()
    return float(lat_s), float(lng_s)


def parse_linestring_wkt(wkt: str) -> tuple[tuple[float, float], ...]:
    inner = wkt.replace("LINESTRING", "").replace("(", "").replace(")", "").strip()
    pairs: list[tuple[float, float]] = []
    for part in inner.split(","):
        lng_s, lat_s = part.strip().split()
        pairs.append((float(lng_s), float(lat_s)))
    return tuple(pairs)


def distance_of(coordinates: tuple[tuple[float, float], ...]) -> int:
    return path_length_m(coordinates)
