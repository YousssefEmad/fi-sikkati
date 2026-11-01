"""Trip create / publish / start / cancel (BR-TRIP-*)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import text

from tests.support.accounts import AccountFactory
from tests.support.http import error_code

pytestmark = pytest.mark.integration

_ORIGIN = {"lat": 30.1935, "lng": 31.4694, "label": "El Obour City"}
_DEST = {"lat": 30.0561, "lng": 31.3300, "label": "Nasr City"}


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
                    5, 'TEST1234', 'ACTIVE', 'APPROVED'
                )
                """
            ),
            {"vid": vehicle_id, "uid": user_id},
        )
        await session.commit()
    return vehicle_id


def _payload(vehicle_id: str, *, hours: int = 4, seats: int = 3) -> dict[str, object]:
    return {
        "vehicleId": vehicle_id,
        "departureAt": (datetime.now(UTC) + timedelta(hours=hours)).isoformat(),
        "totalSeats": seats,
        "stops": [_ORIGIN, _DEST],
        "notes": "Going after work.",
    }


async def test_passenger_cannot_create_a_trip(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    _, session = await accounts.signed_in()
    response = await api_client.post(
        "/api/v1/trips",
        json=_payload(str(uuid4())),
        headers={**session.csrf_headers, "Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 403
    assert error_code(response) == "FORBIDDEN"


async def test_driver_creates_publishes_and_cancels(
    accounts: AccountFactory, api_app: FastAPI
) -> None:
    _, session = await accounts.signed_in()
    me = await accounts.client.get("/api/v1/me")
    vehicle_id = await _grant_driver_with_vehicle(api_app, me.json()["id"])
    created = await accounts.client.post(
        "/api/v1/trips",
        json=_payload(vehicle_id),
        headers={**session.csrf_headers, "Idempotency-Key": str(uuid4())},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["status"] == "DRAFT"
    assert isinstance(body["pricePerSeatMinor"], int)
    assert body["pricePerSeatMinor"] >= 1000
    trip_id = body["id"]

    published = await accounts.client.post(
        f"/api/v1/trips/{trip_id}/publish", headers=session.csrf_headers
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "PUBLISHED"

    too_early = await accounts.client.post(
        f"/api/v1/trips/{trip_id}/start", headers=session.csrf_headers
    )
    assert too_early.status_code == 400
    assert error_code(too_early) == "INVALID_TRANSITION"

    cancelled = await accounts.client.post(
        f"/api/v1/trips/{trip_id}/cancel", headers=session.csrf_headers
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"


async def test_maps_autocomplete_signed_in(accounts: AccountFactory) -> None:
    _, session = await accounts.signed_in()
    response = await accounts.client.get("/api/v1/maps/autocomplete?q=obour")
    assert response.status_code == 200, response.text
    assert response.json()["items"]
    preview = await accounts.client.post(
        "/api/v1/maps/route-preview",
        json={"stops": [_ORIGIN, _DEST]},
        headers=session.csrf_headers,
    )
    assert preview.status_code == 200, preview.text
    estimate = await accounts.client.get(
        f"/api/v1/pricing/estimate?distanceM={preview.json()['distanceM']}"
    )
    assert estimate.status_code == 200
    assert estimate.json()["label"] == "suggested_contribution"
