"""Trip chat: open on publish, join on accept, read-only after cancel (BR-CHAT-*)."""

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


async def test_driver_and_passenger_chat_after_accept(
    accounts: AccountFactory, second_accounts: AccountFactory, api_app: FastAPI
) -> None:
    driver, _driver_id, trip_id = await _publish(api_app, accounts)
    passenger, passenger_id = await _bearer(second_accounts)
    await _approve_identity(api_app, passenger_id)

    inbox = await accounts.client.get("/api/v1/me/conversations", headers=driver.bearer_headers)
    assert inbox.status_code == 200, inbox.text
    assert len(inbox.json()["items"]) == 1
    conversation_id = inbox.json()["items"][0]["id"]

    hidden = await second_accounts.client.get(
        f"/api/v1/conversations/{conversation_id}", headers=passenger.bearer_headers
    )
    assert hidden.status_code == 404

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

    visible = await second_accounts.client.get(
        f"/api/v1/conversations/{conversation_id}", headers=passenger.bearer_headers
    )
    assert visible.status_code == 200, visible.text
    assert visible.json()["isReadOnly"] is False

    client_id = str(uuid4())
    posted = await second_accounts.client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"body": "I'll wait at the gate.", "clientMessageId": client_id},
        headers=passenger.bearer_headers,
    )
    assert posted.status_code == 200, posted.text
    assert posted.json()["body"] == "I'll wait at the gate."
    replay = await second_accounts.client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"body": "I'll wait at the gate.", "clientMessageId": client_id},
        headers=passenger.bearer_headers,
    )
    assert replay.json()["id"] == posted.json()["id"]

    thread = await accounts.client.get(
        f"/api/v1/conversations/{conversation_id}/messages", headers=driver.bearer_headers
    )
    assert thread.status_code == 200
    bodies = [item["body"] for item in thread.json()["items"]]
    assert "I'll wait at the gate." in bodies

    unread = await accounts.client.get(
        "/api/v1/me/notifications/unread-count", headers=driver.bearer_headers
    )
    assert unread.status_code == 200
    assert unread.json()["unread"] >= 1

    cancelled = await accounts.client.post(
        f"/api/v1/trips/{trip_id}/cancel", headers=driver.bearer_headers
    )
    assert cancelled.status_code == 200
    closed = await second_accounts.client.get(
        f"/api/v1/conversations/{conversation_id}", headers=passenger.bearer_headers
    )
    assert closed.json()["isReadOnly"] is True
    blocked = await second_accounts.client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"body": "Are we still going?", "clientMessageId": str(uuid4())},
        headers=passenger.bearer_headers,
    )
    assert blocked.status_code == 409
    assert error_code(blocked) == "CONVERSATION_READ_ONLY"


async def test_join_request_notifies_the_driver(
    accounts: AccountFactory, second_accounts: AccountFactory, api_app: FastAPI
) -> None:
    driver, _driver_id, trip_id = await _publish(api_app, accounts)
    passenger, passenger_id = await _bearer(second_accounts)
    await _approve_identity(api_app, passenger_id)
    created = await second_accounts.client.post(
        f"/api/v1/trips/{trip_id}/join-requests",
        json={"seatsRequested": 1, "pickup": _ORIGIN, "dropoff": _DEST},
        headers={**passenger.bearer_headers, "Idempotency-Key": str(uuid4())},
    )
    assert created.status_code == 200, created.text
    notes = await accounts.client.get("/api/v1/me/notifications", headers=driver.bearer_headers)
    assert notes.status_code == 200, notes.text
    types = [item["type"] for item in notes.json()["items"]]
    assert "JOIN_REQUEST_RECEIVED" in types
    marked = await accounts.client.post(
        "/api/v1/me/notifications/read", json={}, headers=driver.bearer_headers
    )
    assert marked.status_code == 200
    assert marked.json()["marked"] >= 1
