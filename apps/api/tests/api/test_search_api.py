"""Published-trip search (FR-SRCH-*, BR-MATCH-*)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import text

from tests.support.accounts import AccountFactory
from tests.support.http import error_code

pytestmark = pytest.mark.integration

_ORIGIN_LAT = 30.1935
_ORIGIN_LNG = 31.4694
_DEST_LAT = 30.0561
_DEST_LNG = 31.3300
_ALEX_LAT = 31.2001
_ALEX_LNG = 29.9187
_ORIGIN = {"lat": _ORIGIN_LAT, "lng": _ORIGIN_LNG, "label": "El Obour City"}
_DEST = {"lat": _DEST_LAT, "lng": _DEST_LNG, "label": "Nasr City"}
_CAIRO = ZoneInfo("Africa/Cairo")


async def _grant_driver_with_vehicle(api_app: FastAPI, user_id: str) -> str:
    vehicle_id = str(uuid4())
    async with api_app.state.database.session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO user_roles (user_id, role) VALUES (:id, 'DRIVER') "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": user_id},
        )
        await session.execute(
            text(
                """
                INSERT INTO vehicles (
                    id, owner_user_id, make, model, year, color, vehicle_type,
                    seat_capacity, plate_number, status, verification_status
                ) VALUES (
                    :vid, :uid, 'Hyundai', 'Elantra', 2020, 'white', 'SEDAN',
                    5, :plate, 'ACTIVE', 'APPROVED'
                )
                """
            ),
            {"vid": vehicle_id, "uid": user_id, "plate": f"S{uuid4().hex[:7].upper()}"},
        )
        await session.commit()
    return vehicle_id


async def _publish(accounts: AccountFactory, api_app: FastAPI) -> dict[str, Any]:
    _, session = await accounts.signed_in()
    me = await accounts.client.get("/api/v1/me")
    vehicle_id = await _grant_driver_with_vehicle(api_app, me.json()["id"])
    created = await accounts.client.post(
        "/api/v1/trips",
        json={
            "vehicleId": vehicle_id,
            "departureAt": (datetime.now(UTC) + timedelta(hours=6)).isoformat(),
            "totalSeats": 3,
            "stops": [_ORIGIN, _DEST],
        },
        headers={**session.csrf_headers, "Idempotency-Key": str(uuid4())},
    )
    assert created.status_code == 200, created.text
    published = await accounts.client.post(
        f"/api/v1/trips/{created.json()['id']}/publish", headers=session.csrf_headers
    )
    assert published.status_code == 200, published.text
    body = published.json()
    assert isinstance(body, dict)
    return cast(dict[str, Any], body)


def _query(
    trip: dict[str, Any], *, drop_lat: float, drop_lng: float
) -> dict[str, str | int | float]:
    departure = datetime.fromisoformat(str(trip["departureAt"]).replace("Z", "+00:00"))
    local = departure.astimezone(_CAIRO)
    return {
        "pickupLat": _ORIGIN_LAT,
        "pickupLng": _ORIGIN_LNG,
        "dropoffLat": drop_lat,
        "dropoffLng": drop_lng,
        "date": local.date().isoformat(),
        "time": local.strftime("%H:%M"),
        "seats": 1,
    }


async def test_anonymous_search_is_unauthenticated(api_client: AsyncClient) -> None:
    response = await api_client.get(
        "/api/v1/search/trips",
        params={
            "pickupLat": _ORIGIN_LAT,
            "pickupLng": _ORIGIN_LNG,
            "dropoffLat": _DEST_LAT,
            "dropoffLng": _DEST_LNG,
            "date": "2026-10-03",
        },
    )
    assert response.status_code == 401
    assert error_code(response) == "UNAUTHENTICATED"


async def test_published_trip_matches_along_its_route(
    accounts: AccountFactory, api_app: FastAPI
) -> None:
    trip = await _publish(accounts, api_app)
    passenger, session = await accounts.signed_in()
    del passenger, session
    response = await accounts.client.get(
        "/api/v1/search/trips", params=_query(trip, drop_lat=_DEST_LAT, drop_lng=_DEST_LNG)
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 1
    hit = items[0]
    assert hit["tripId"] == trip["id"]
    assert hit["matchKind"] == "EXACT"
    assert hit["driver"]["displayName"]
    assert "plateNumber" not in hit
    assert hit["originLat"] != trip["originLat"] or hit["originLng"] != trip["originLng"]


async def test_far_dropoff_is_not_compatible(accounts: AccountFactory, api_app: FastAPI) -> None:
    trip = await _publish(accounts, api_app)
    await accounts.signed_in()
    response = await accounts.client.get(
        "/api/v1/search/trips",
        params=_query(trip, drop_lat=_ALEX_LAT, drop_lng=_ALEX_LNG),
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"] == []


async def test_midpoint_is_on_route_not_exact(accounts: AccountFactory, api_app: FastAPI) -> None:
    trip = await _publish(accounts, api_app)
    await accounts.signed_in()
    mid_lat = (_ORIGIN_LAT + _DEST_LAT) / 2
    mid_lng = (_ORIGIN_LNG + _DEST_LNG) / 2
    departure = datetime.fromisoformat(str(trip["departureAt"]).replace("Z", "+00:00"))
    local = departure.astimezone(_CAIRO)
    response = await accounts.client.get(
        "/api/v1/search/trips",
        params={
            "pickupLat": mid_lat,
            "pickupLng": mid_lng,
            "dropoffLat": _DEST_LAT,
            "dropoffLng": _DEST_LNG,
            "date": local.date().isoformat(),
            "time": local.strftime("%H:%M"),
        },
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["matchKind"] == "ON_ROUTE"


async def test_min_rating_hides_drivers_below_the_threshold(
    accounts: AccountFactory, api_app: FastAPI
) -> None:
    trip = await _publish(accounts, api_app)
    await accounts.signed_in()
    params = _query(trip, drop_lat=_DEST_LAT, drop_lng=_DEST_LNG)
    params["minRating"] = 4
    response = await accounts.client.get("/api/v1/search/trips", params=params)
    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_draft_is_hidden_from_search(accounts: AccountFactory, api_app: FastAPI) -> None:
    _, session = await accounts.signed_in()
    me = await accounts.client.get("/api/v1/me")
    vehicle_id = await _grant_driver_with_vehicle(api_app, me.json()["id"])
    created = await accounts.client.post(
        "/api/v1/trips",
        json={
            "vehicleId": vehicle_id,
            "departureAt": (datetime.now(UTC) + timedelta(hours=6)).isoformat(),
            "totalSeats": 3,
            "stops": [_ORIGIN, _DEST],
        },
        headers={**session.csrf_headers, "Idempotency-Key": str(uuid4())},
    )
    assert created.status_code == 200, created.text
    await accounts.signed_in()
    departure = datetime.fromisoformat(created.json()["departureAt"].replace("Z", "+00:00"))
    local = departure.astimezone(_CAIRO)
    response = await accounts.client.get(
        "/api/v1/search/trips",
        params={
            "pickupLat": _ORIGIN_LAT,
            "pickupLng": _ORIGIN_LNG,
            "dropoffLat": _DEST_LAT,
            "dropoffLng": _DEST_LNG,
            "date": local.date().isoformat(),
            "time": local.strftime("%H:%M"),
        },
    )
    assert response.status_code == 200
    assert response.json()["items"] == []
