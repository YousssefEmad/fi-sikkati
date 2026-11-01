from __future__ import annotations

from uuid import UUID

from app.modules.maps.fake import FakeMapProvider
from app.modules.maps.geo import deterministic_jitter, haversine_m
from app.modules.maps.ports import GeoPoint


def test_haversine_el_obour_to_nasr_city_is_tens_of_kilometres() -> None:
    metres = haversine_m(30.1935, 31.4694, 30.0561, 31.3300)
    assert 15_000 < metres < 40_000


def test_jitter_is_stable_per_trip() -> None:
    trip_id = UUID("01924000-0000-7000-8000-000000000099")
    first = deterministic_jitter(30.19, 31.47, trip_id=trip_id, radius_m=500)
    second = deterministic_jitter(30.19, 31.47, trip_id=trip_id, radius_m=500)
    assert first == second
    assert first != (30.19, 31.47)


async def test_fake_autocomplete_and_route() -> None:
    provider = FakeMapProvider()
    hits = await provider.autocomplete("عبور", locale="ar")
    assert hits
    origin = hits[0]
    dest = (await provider.autocomplete("نصر", locale="ar"))[0]
    route = await provider.route((origin, dest))
    assert route.distance_m > 0
    assert route.provider == "fake"
    assert len(route.coordinates) == 2


async def test_fake_geocode_lat_lng() -> None:
    provider = FakeMapProvider()
    point = await provider.geocode("30.04, 31.23", locale="en")
    assert isinstance(point, GeoPoint)
    assert point.lat == 30.04
