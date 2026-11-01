"""Ratings, reports and blocks (BR-SAFE-*)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from sqlalchemy import text

from tests.support.accounts import AccountFactory, Session
from tests.support.http import error_code

pytestmark = pytest.mark.integration

_ORIGIN = {"lat": 30.1935, "lng": 31.4694, "label": "El Obour City"}
_DEST = {"lat": 30.0561, "lng": 31.3300, "label": "Nasr City"}


async def _approve_identity(api_app: FastAPI, user_id: str) -> None:
    async with api_app.state.database.session_factory() as session:
        await session.execute(
            text("UPDATE users SET identity_verification_status = 'APPROVED' WHERE id = :id"),
            {"id": user_id},
        )
        await session.commit()


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
            {"vid": vehicle_id, "uid": user_id, "plate": uuid4().hex[:8]},
        )
        await session.commit()
    return vehicle_id


async def _bearer(factory: AccountFactory) -> tuple[Session, str]:
    _credentials, session = await factory.signed_in(as_api_client=True)
    response = await factory.client.get("/api/v1/me", headers=session.bearer_headers)
    assert response.status_code == 200, response.text
    return session, str(response.json()["id"])


async def _publish(
    api_app: FastAPI, factory: AccountFactory, *, seats: int = 2
) -> tuple[Session, str, str]:
    session, user_id = await _bearer(factory)
    await _approve_identity(api_app, user_id)
    vehicle_id = await _grant_driver_with_vehicle(api_app, user_id)
    created = await factory.client.post(
        "/api/v1/trips",
        json={
            "vehicleId": vehicle_id,
            "departureAt": (datetime.now(UTC) + timedelta(hours=5)).isoformat(),
            "totalSeats": seats,
            "stops": [_ORIGIN, _DEST],
        },
        headers={**session.bearer_headers, "Idempotency-Key": str(uuid4())},
    )
    assert created.status_code == 200, created.text
    trip_id = str(created.json()["id"])
    published = await factory.client.post(
        f"/api/v1/trips/{trip_id}/publish", headers=session.bearer_headers
    )
    assert published.status_code == 200, published.text
    return session, user_id, trip_id


async def test_block_hides_the_driver_from_join_and_search(
    accounts: AccountFactory, second_accounts: AccountFactory, api_app: FastAPI
) -> None:
    driver, driver_id, trip_id = await _publish(api_app, accounts)
    passenger, passenger_id = await _bearer(second_accounts)
    await _approve_identity(api_app, passenger_id)

    blocked = await second_accounts.client.post(
        "/api/v1/me/blocks",
        json={"userId": driver_id},
        headers=passenger.bearer_headers,
    )
    assert blocked.status_code == 204, blocked.text

    listed = await second_accounts.client.get("/api/v1/me/blocks", headers=passenger.bearer_headers)
    assert listed.status_code == 200
    assert listed.json()["items"][0]["userId"] == driver_id

    hidden = await second_accounts.client.post(
        f"/api/v1/trips/{trip_id}/join-requests",
        json={"seatsRequested": 1, "pickup": _ORIGIN, "dropoff": _DEST},
        headers={**passenger.bearer_headers, "Idempotency-Key": str(uuid4())},
    )
    assert hidden.status_code == 404

    trip = await accounts.client.get(f"/api/v1/trips/{trip_id}", headers=driver.bearer_headers)
    departure = datetime.fromisoformat(str(trip.json()["departureAt"]).replace("Z", "+00:00"))
    local = departure.astimezone(ZoneInfo("Africa/Cairo"))
    search = await second_accounts.client.get(
        "/api/v1/search/trips",
        params={
            "pickupLat": _ORIGIN["lat"],
            "pickupLng": _ORIGIN["lng"],
            "dropoffLat": _DEST["lat"],
            "dropoffLng": _DEST["lng"],
            "date": local.date().isoformat(),
            "time": local.strftime("%H:%M"),
        },
        headers=passenger.bearer_headers,
    )
    assert search.status_code == 200, search.text
    assert search.json()["items"] == []

    removed = await second_accounts.client.delete(
        f"/api/v1/me/blocks/{driver_id}", headers=passenger.bearer_headers
    )
    assert removed.status_code == 204


async def test_report_a_user_and_list_own(
    accounts: AccountFactory, second_accounts: AccountFactory
) -> None:
    _owner, owner_session = await accounts.signed_in(as_api_client=True)
    me = await accounts.client.get("/api/v1/me", headers=owner_session.bearer_headers)
    owner_id = me.json()["id"]
    _reporter, reporter = await second_accounts.signed_in(as_api_client=True)
    created = await second_accounts.client.post(
        "/api/v1/reports",
        json={"targetType": "USER", "targetId": owner_id, "reason": "SPAM", "description": "Ads."},
        headers=reporter.bearer_headers,
    )
    assert created.status_code == 200, created.text
    assert created.json()["status"] == "OPEN"
    mine = await second_accounts.client.get("/api/v1/me/reports", headers=reporter.bearer_headers)
    assert mine.status_code == 200
    assert len(mine.json()["items"]) == 1
    again = await second_accounts.client.post(
        "/api/v1/reports",
        json={"targetType": "USER", "targetId": owner_id, "reason": "SPAM"},
        headers=reporter.bearer_headers,
    )
    assert again.status_code == 400


async def test_rate_after_completed_trip(
    accounts: AccountFactory, second_accounts: AccountFactory, api_app: FastAPI
) -> None:
    driver, driver_id, trip_id = await _publish(api_app, accounts)
    passenger, passenger_id = await _bearer(second_accounts)
    await _approve_identity(api_app, passenger_id)
    created = await second_accounts.client.post(
        f"/api/v1/trips/{trip_id}/join-requests",
        json={"seatsRequested": 1, "pickup": _ORIGIN, "dropoff": _DEST},
        headers={**passenger.bearer_headers, "Idempotency-Key": str(uuid4())},
    )
    assert created.status_code == 200, created.text
    accepted = await accounts.client.post(
        f"/api/v1/join-requests/{created.json()['id']}/accept", headers=driver.bearer_headers
    )
    assert accepted.status_code == 200, accepted.text

    async with api_app.state.database.session_factory() as session:
        await session.execute(
            text("UPDATE trips SET departure_at = now() - interval '1 minute' WHERE id = :id"),
            {"id": trip_id},
        )
        await session.commit()

    started = await accounts.client.post(
        f"/api/v1/trips/{trip_id}/start", headers=driver.bearer_headers
    )
    assert started.status_code == 200, started.text
    completed = await accounts.client.post(
        f"/api/v1/trips/{trip_id}/complete", headers=driver.bearer_headers
    )
    assert completed.status_code == 200, completed.text

    too_soon_self = await accounts.client.post(
        f"/api/v1/trips/{trip_id}/ratings",
        json={"rateeId": driver_id, "overall": 5},
        headers=driver.bearer_headers,
    )
    assert too_soon_self.status_code == 400

    rated = await second_accounts.client.post(
        f"/api/v1/trips/{trip_id}/ratings",
        json={"rateeId": driver_id, "overall": 5, "punctuality": 4, "comment": "On time."},
        headers=passenger.bearer_headers,
    )
    assert rated.status_code == 200, rated.text
    assert rated.json()["overall"] == 5

    duplicate = await second_accounts.client.post(
        f"/api/v1/trips/{trip_id}/ratings",
        json={"rateeId": driver_id, "overall": 3},
        headers=passenger.bearer_headers,
    )
    assert duplicate.status_code == 409
    assert error_code(duplicate) == "ALREADY_RATED"

    summary = await second_accounts.client.get(
        f"/api/v1/users/{driver_id}/ratings/summary", headers=passenger.bearer_headers
    )
    assert summary.status_code == 200
    body = summary.json()
    assert body["visible"] is False
    assert body["count"] == 0
    assert body["average"] is None
