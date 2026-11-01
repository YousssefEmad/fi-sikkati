"""Spheroid helpers used by the fake provider and location-privacy jitter (BR-MATCH-08)."""

from __future__ import annotations

import math
from itertools import pairwise
from uuid import UUID

EARTH_RADIUS_M = 6_371_000
DEFAULT_SPEED_M_S = 13.89  # ~50 km/h urban average for duration estimates


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return round(2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a))))


def destination(
    lat: float, lng: float, distance_m: float, bearing_rad: float
) -> tuple[float, float]:
    """Point ``distance_m`` from ``(lat, lng)`` along ``bearing_rad`` (clockwise from north)."""
    angular = distance_m / EARTH_RADIUS_M
    phi1 = math.radians(lat)
    lambda1 = math.radians(lng)
    phi2 = math.asin(
        math.sin(phi1) * math.cos(angular)
        + math.cos(phi1) * math.sin(angular) * math.cos(bearing_rad)
    )
    lambda2 = lambda1 + math.atan2(
        math.sin(bearing_rad) * math.sin(angular) * math.cos(phi1),
        math.cos(angular) - math.sin(phi1) * math.sin(phi2),
    )
    return (math.degrees(phi2), (math.degrees(lambda2) + 540) % 360 - 180)


def path_length_m(coordinates: tuple[tuple[float, float], ...]) -> int:
    """``coordinates`` are ``(lng, lat)`` pairs."""
    total = 0
    for (lng_a, lat_a), (lng_b, lat_b) in pairwise(coordinates):
        total += haversine_m(lat_a, lng_a, lat_b, lng_b)
    return total


def duration_s_for(distance_m: int) -> int:
    return max(60, round(distance_m / DEFAULT_SPEED_M_S))


def deterministic_jitter(
    lat: float, lng: float, *, trip_id: UUID, radius_m: int
) -> tuple[float, float]:
    """Stable offset inside ``radius_m`` so the same trip never averages toward the exact point."""
    seed = int(trip_id.hex, 16)
    bearing = ((seed % 36000) / 100.0) * math.pi / 180.0
    distance = ((seed // 36000) % (radius_m + 1)) * 0.85 + radius_m * 0.15
    return destination(lat, lng, distance, bearing)
