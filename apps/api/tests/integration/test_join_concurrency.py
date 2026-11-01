"""Seat consistency under concurrent accepts (testing.md §5, BR-JOIN-06)."""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import text

from app.core.authz.permissions import Role
from app.core.config import Settings
from app.core.errors import DuplicateRequestError, RequestNotPendingError, SeatUnavailableError
from app.modules.bookings.repository import BookingRepository
from app.modules.bookings.service import BookingService, JoinPoint
from tests.api.test_join_api import _DEST, _ORIGIN, _approve_identity, _bearer, _join_body, _publish
from tests.support.accounts import AccountFactory

pytestmark = pytest.mark.integration

_POINT_PICKUP = JoinPoint(lat=_ORIGIN["lat"], lng=_ORIGIN["lng"], label=str(_ORIGIN["label"]))
_POINT_DROPOFF = JoinPoint(lat=_DEST["lat"], lng=_DEST["lng"], label=str(_DEST["label"]))


async def _passenger_request(factory: AccountFactory, api_app: FastAPI, trip_id: str) -> str:
    session, user_id = await _bearer(factory)
    await _approve_identity(api_app, user_id)
    created = await factory.client.post(
        f"/api/v1/trips/{trip_id}/join-requests",
        json=_join_body(),
        headers={**session.bearer_headers, "Idempotency-Key": str(uuid4())},
    )
    assert created.status_code == 200, created.text
    return str(created.json()["id"])


async def test_one_seat_cannot_be_accepted_twice(
    accounts: AccountFactory,
    second_accounts: AccountFactory,
    api_app: FastAPI,
    api_client: AsyncClient,
) -> None:
    driver, _driver_id, trip_id = await _publish(api_app, accounts, seats=1)
    first = await _passenger_request(second_accounts, api_app, trip_id)
    # Reuse the primary client for another passenger; the driver's bearer token is already saved.
    second = await _passenger_request(accounts, api_app, trip_id)

    async def accept(request_id: str) -> int:
        response = await api_client.post(
            f"/api/v1/join-requests/{request_id}/accept",
            headers=driver.bearer_headers,
        )
        return response.status_code

    statuses = await asyncio.gather(accept(first), accept(second))
    assert sorted(statuses) == [200, 409]

    async with api_app.state.database.session_factory() as session:
        trip = (
            await session.execute(
                text("SELECT status, total_seats, available_seats FROM trips WHERE id = :id"),
                {"id": trip_id},
            )
        ).one()
        accepted = await session.scalar(
            text(
                """
                SELECT coalesce(sum(seats_requested), 0)
                FROM trip_join_requests
                WHERE trip_id = :id AND status = 'ACCEPTED'
                """
            ),
            {"id": trip_id},
        )
    assert trip.status == "FULL"
    assert trip.available_seats == 0
    assert int(accepted or 0) == trip.total_seats - trip.available_seats


async def _clone_passenger(api_app: FastAPI, source_id: str) -> UUID:
    new_id = uuid4()
    email = f"clone-{new_id.hex[:12]}@example.com"
    async with api_app.state.database.session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO users (
                    id, email, password_hash, status, email_verified_at,
                    identity_verification_status, date_of_birth, terms_version,
                    privacy_version, legal_accepted_at, locale
                )
                SELECT
                    :new_id, :email, password_hash, status, email_verified_at,
                    'APPROVED', date_of_birth, terms_version, privacy_version,
                    legal_accepted_at, locale
                FROM users WHERE id = :source
                """
            ),
            {"new_id": new_id, "email": email, "source": source_id},
        )
        await session.execute(
            text(
                """
                INSERT INTO user_profiles (user_id, display_name, full_name, display_name_key)
                SELECT :new_id, display_name, full_name, :name_key
                FROM user_profiles WHERE user_id = :source
                """
            ),
            {"new_id": new_id, "source": source_id, "name_key": str(new_id)},
        )
        await session.execute(
            text("INSERT INTO user_roles (user_id, role) VALUES (:new_id, 'PASSENGER')"),
            {"new_id": new_id},
        )
        await session.commit()
    return new_id


def _booking(session: object, settings: Settings) -> BookingService:
    return BookingService(BookingRepository(session), settings)  # type: ignore[arg-type]


async def _create_request(api_app: FastAPI, passenger_id: UUID, trip_id: UUID) -> UUID:
    settings = api_app.state.settings
    async with api_app.state.database.session_factory() as session:
        view = await _booking(session, settings).create(
            passenger_id=passenger_id,
            roles=frozenset({Role.PASSENGER}),
            email_verified=True,
            phone_verified=True,
            trip_id=trip_id,
            seats_requested=1,
            pickup=_POINT_PICKUP,
            dropoff=_POINT_DROPOFF,
            note="At the gate.",
            idempotency_key=str(uuid4()),
        )
        await session.commit()
        return view.id


async def test_parallel_accepts_never_overbook(accounts: AccountFactory, api_app: FastAPI) -> None:
    _driver, _driver_id, trip_id = await _publish(api_app, accounts, seats=3)
    seed, seed_id = await _bearer(accounts)
    await _approve_identity(api_app, seed_id)
    del seed
    passenger_ids = [UUID(seed_id)]
    for _ in range(9):
        passenger_ids.append(await _clone_passenger(api_app, seed_id))
    request_ids = [
        await _create_request(api_app, passenger_id, UUID(trip_id))
        for passenger_id in passenger_ids
    ]
    settings = api_app.state.settings

    async def accept(request_id: UUID) -> str:
        async with api_app.state.database.session_factory() as session:
            try:
                await _booking(session, settings).accept(request_id, driver_id=UUID(_driver_id))
                await session.commit()
            except SeatUnavailableError:
                return "SEAT_UNAVAILABLE"
            except RequestNotPendingError:
                return "REQUEST_NOT_PENDING"
            return "ACCEPTED"

    outcomes = await asyncio.gather(*(accept(request_id) for request_id in request_ids))
    assert outcomes.count("ACCEPTED") == 3

    async with api_app.state.database.session_factory() as session:
        trip = (
            await session.execute(
                text("SELECT total_seats, available_seats FROM trips WHERE id = :id"),
                {"id": trip_id},
            )
        ).one()
        accepted = await session.scalar(
            text(
                """
                SELECT coalesce(sum(seats_requested), 0)
                FROM trip_join_requests
                WHERE trip_id = :id AND status = 'ACCEPTED'
                """
            ),
            {"id": trip_id},
        )
    assert trip.available_seats == 0
    assert 0 <= trip.available_seats <= trip.total_seats
    assert int(accepted or 0) == trip.total_seats - trip.available_seats


async def test_same_idempotency_key_in_parallel_creates_one_row(
    accounts: AccountFactory, second_accounts: AccountFactory, api_app: FastAPI
) -> None:
    _driver, _driver_id, trip_id = await _publish(api_app, accounts, seats=3)
    _passenger, passenger_id = await _bearer(second_accounts)
    await _approve_identity(api_app, passenger_id)
    key = str(uuid4())
    settings = api_app.state.settings

    async def create() -> UUID:
        async with api_app.state.database.session_factory() as session:
            service = _booking(session, settings)
            try:
                view = await service.create(
                    passenger_id=UUID(passenger_id),
                    roles=frozenset({Role.PASSENGER}),
                    email_verified=True,
                    phone_verified=True,
                    trip_id=UUID(trip_id),
                    seats_requested=1,
                    pickup=_POINT_PICKUP,
                    dropoff=_POINT_DROPOFF,
                    note="At the gate.",
                    idempotency_key=key,
                )
            except DuplicateRequestError:
                existing = await BookingRepository(session).get_by_idempotency(
                    UUID(passenger_id), key
                )
                assert existing is not None
                await session.rollback()
                return existing.id
            await session.commit()
            return view.id

    ids = await asyncio.gather(*(create() for _ in range(5)))
    assert len(set(ids)) == 1

    async with api_app.state.database.session_factory() as session:
        count = await session.scalar(
            text(
                """
                SELECT count(*) FROM trip_join_requests
                WHERE passenger_id = :passenger AND idempotency_key = :key
                """
            ),
            {"passenger": passenger_id, "key": key},
        )
    assert int(count or 0) == 1
