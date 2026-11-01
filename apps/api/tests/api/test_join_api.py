"""Join requests: create, accept, reject, cancel, and seat release (BR-JOIN-*)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

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


def _trip_body(vehicle_id: str, *, hours: int = 5, seats: int = 2) -> dict[str, object]:
    return {
        "vehicleId": vehicle_id,
        "departureAt": (datetime.now(UTC) + timedelta(hours=hours)).isoformat(),
        "totalSeats": seats,
        "stops": [_ORIGIN, _DEST],
        "notes": "After work.",
    }


def _join_body(*, seats: int = 1) -> dict[str, object]:
    return {"seatsRequested": seats, "pickup": _ORIGIN, "dropoff": _DEST, "note": "At the gate."}


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
        json=_trip_body(vehicle_id, seats=seats),
        headers={**session.bearer_headers, "Idempotency-Key": str(uuid4())},
    )
    assert created.status_code == 200, created.text
    trip_id = str(created.json()["id"])
    published = await factory.client.post(
        f"/api/v1/trips/{trip_id}/publish", headers=session.bearer_headers
    )
    assert published.status_code == 200, published.text
    return session, user_id, trip_id


async def test_passenger_requests_and_driver_accepts_the_last_seats(
    accounts: AccountFactory, second_accounts: AccountFactory, api_app: FastAPI
) -> None:
    driver, _driver_id, trip_id = await _publish(api_app, accounts, seats=1)
    passenger, passenger_id = await _bearer(second_accounts)
    await _approve_identity(api_app, passenger_id)

    hidden = await second_accounts.client.get(
        f"/api/v1/trips/{trip_id}", headers=passenger.bearer_headers
    )
    assert hidden.status_code == 200
    assert hidden.json()["exactStops"] is False

    created = await second_accounts.client.post(
        f"/api/v1/trips/{trip_id}/join-requests",
        json=_join_body(),
        headers={**passenger.bearer_headers, "Idempotency-Key": str(uuid4())},
    )
    assert created.status_code == 200, created.text
    request_id = created.json()["id"]
    assert created.json()["status"] == "PENDING"

    accepted = await accounts.client.post(
        f"/api/v1/join-requests/{request_id}/accept", headers=driver.bearer_headers
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "ACCEPTED"

    trip = await accounts.client.get(f"/api/v1/trips/{trip_id}", headers=driver.bearer_headers)
    assert trip.json()["availableSeats"] == 0
    assert trip.json()["status"] == "FULL"

    exact = await second_accounts.client.get(
        f"/api/v1/trips/{trip_id}", headers=passenger.bearer_headers
    )
    assert exact.json()["exactStops"] is True

    mine = await second_accounts.client.get(
        "/api/v1/me/trips", params={"role": "passenger"}, headers=passenger.bearer_headers
    )
    assert mine.status_code == 200
    assert [item["id"] for item in mine.json()["items"]] == [trip_id]

    again = await accounts.client.post(
        f"/api/v1/join-requests/{request_id}/accept", headers=driver.bearer_headers
    )
    assert again.status_code == 409
    assert error_code(again) == "REQUEST_NOT_PENDING"


async def test_idempotent_create_and_duplicate_are_distinct(
    accounts: AccountFactory, second_accounts: AccountFactory, api_app: FastAPI
) -> None:
    _driver, _driver_id, trip_id = await _publish(api_app, accounts, seats=2)
    passenger, passenger_id = await _bearer(second_accounts)
    await _approve_identity(api_app, passenger_id)
    key = str(uuid4())
    headers = {**passenger.bearer_headers, "Idempotency-Key": key}
    first = await second_accounts.client.post(
        f"/api/v1/trips/{trip_id}/join-requests", json=_join_body(), headers=headers
    )
    second = await second_accounts.client.post(
        f"/api/v1/trips/{trip_id}/join-requests", json=_join_body(), headers=headers
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["id"] == second.json()["id"]

    changed = await second_accounts.client.post(
        f"/api/v1/trips/{trip_id}/join-requests",
        json=_join_body(seats=2),
        headers=headers,
    )
    assert changed.status_code == 409
    assert error_code(changed) == "IDEMPOTENCY_CONFLICT"

    other_key = await second_accounts.client.post(
        f"/api/v1/trips/{trip_id}/join-requests",
        json=_join_body(),
        headers={**passenger.bearer_headers, "Idempotency-Key": str(uuid4())},
    )
    assert other_key.status_code == 409
    assert error_code(other_key) == "DUPLICATE_REQUEST"


async def test_identity_email_and_own_trip_are_rejected(
    accounts: AccountFactory, second_accounts: AccountFactory, api_app: FastAPI
) -> None:
    driver, driver_id, trip_id = await _publish(api_app, accounts, seats=2)
    own = await accounts.client.post(
        f"/api/v1/trips/{trip_id}/join-requests",
        json=_join_body(),
        headers={**driver.bearer_headers, "Idempotency-Key": str(uuid4())},
    )
    assert own.status_code == 403

    passenger, _passenger_id = await _bearer(second_accounts)
    unverified = await second_accounts.client.post(
        f"/api/v1/trips/{trip_id}/join-requests",
        json=_join_body(),
        headers={**passenger.bearer_headers, "Idempotency-Key": str(uuid4())},
    )
    assert unverified.status_code == 403
    assert error_code(unverified) == "IDENTITY_NOT_VERIFIED"
    del driver_id


async def test_reject_and_passenger_cancel_release_seats(
    accounts: AccountFactory, second_accounts: AccountFactory, api_app: FastAPI
) -> None:
    driver, _driver_id, trip_id = await _publish(api_app, accounts, seats=1)
    passenger, passenger_id = await _bearer(second_accounts)
    await _approve_identity(api_app, passenger_id)
    created = await second_accounts.client.post(
        f"/api/v1/trips/{trip_id}/join-requests",
        json=_join_body(),
        headers={**passenger.bearer_headers, "Idempotency-Key": str(uuid4())},
    )
    request_id = created.json()["id"]
    rejected = await accounts.client.post(
        f"/api/v1/join-requests/{request_id}/reject", headers=driver.bearer_headers
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"

    again = await second_accounts.client.post(
        f"/api/v1/trips/{trip_id}/join-requests",
        json=_join_body(),
        headers={**passenger.bearer_headers, "Idempotency-Key": str(uuid4())},
    )
    assert again.status_code == 200, again.text
    accepted = await accounts.client.post(
        f"/api/v1/join-requests/{again.json()['id']}/accept", headers=driver.bearer_headers
    )
    assert accepted.json()["status"] == "ACCEPTED"
    full = await accounts.client.get(f"/api/v1/trips/{trip_id}", headers=driver.bearer_headers)
    assert full.json()["status"] == "FULL"

    cancelled = await second_accounts.client.post(
        f"/api/v1/join-requests/{again.json()['id']}/cancel", headers=passenger.bearer_headers
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "CANCELLED"
    assert cancelled.json()["cancelledBy"] == "PASSENGER"
    assert isinstance(cancelled.json()["minutesBeforeDepartureAtCancel"], int)

    restored = await accounts.client.get(f"/api/v1/trips/{trip_id}", headers=driver.bearer_headers)
    assert restored.json()["status"] == "PUBLISHED"
    assert restored.json()["availableSeats"] == 1


async def test_cancelling_the_trip_cancels_pending_requests(
    accounts: AccountFactory, second_accounts: AccountFactory, api_app: FastAPI
) -> None:
    driver, _driver_id, trip_id = await _publish(api_app, accounts, seats=2)
    passenger, passenger_id = await _bearer(second_accounts)
    await _approve_identity(api_app, passenger_id)
    created = await second_accounts.client.post(
        f"/api/v1/trips/{trip_id}/join-requests",
        json=_join_body(),
        headers={**passenger.bearer_headers, "Idempotency-Key": str(uuid4())},
    )
    request_id = created.json()["id"]
    cancelled = await accounts.client.post(
        f"/api/v1/trips/{trip_id}/cancel", headers=driver.bearer_headers
    )
    assert cancelled.status_code == 200, cancelled.text
    detail = await second_accounts.client.get(
        f"/api/v1/join-requests/{request_id}", headers=passenger.bearer_headers
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "CANCELLED"
    assert detail.json()["cancelledBy"] == "DRIVER"


async def test_stranger_cannot_read_a_request(
    accounts: AccountFactory, second_accounts: AccountFactory, api_app: FastAPI
) -> None:
    driver, _driver_id, trip_id = await _publish(api_app, accounts, seats=2)
    passenger, passenger_id = await _bearer(second_accounts)
    await _approve_identity(api_app, passenger_id)
    created = await second_accounts.client.post(
        f"/api/v1/trips/{trip_id}/join-requests",
        json=_join_body(),
        headers={**passenger.bearer_headers, "Idempotency-Key": str(uuid4())},
    )
    assert created.status_code == 200, created.text
    request_id = created.json()["id"]

    visible = await accounts.client.get(
        f"/api/v1/join-requests/{request_id}", headers=driver.bearer_headers
    )
    assert visible.status_code == 200

    stranger, _stranger_id = await _bearer(accounts)
    hidden = await accounts.client.get(
        f"/api/v1/join-requests/{request_id}", headers=stranger.bearer_headers
    )
    assert hidden.status_code == 404
    assert error_code(hidden) == "NOT_FOUND"
