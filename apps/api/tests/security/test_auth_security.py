"""CSRF, refresh-token reuse, rate limits, enumeration and IDOR (security.md §12)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.core.security import CSRF_HEADER_NAME, AccessTokenService
from tests.support.accounts import DEFAULT_PASSWORD, AccountFactory
from tests.support.http import error_code

pytestmark = pytest.mark.integration


# --- CSRF -------------------------------------------------------------------------------------


async def test_cookie_authenticated_mutation_without_csrf_is_rejected(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    await accounts.signed_in()

    response = await api_client.patch("/api/v1/me", json={"city": "El Obour"})

    assert response.status_code == 403
    assert error_code(response) == "CSRF_FAILED"


async def test_cookie_authenticated_mutation_with_a_foreign_csrf_token_is_rejected(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    await accounts.signed_in()

    response = await api_client.patch(
        "/api/v1/me",
        json={"city": "El Obour"},
        headers={CSRF_HEADER_NAME: "not-the-token-for-this-session"},
    )

    assert response.status_code == 403
    assert error_code(response) == "CSRF_FAILED"


async def test_cross_site_origin_is_rejected_even_with_a_valid_csrf_token(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    _, session = await accounts.signed_in()

    response = await api_client.patch(
        "/api/v1/me",
        json={"city": "El Obour"},
        headers={**session.csrf_headers, "Origin": "https://evil.example"},
    )

    assert response.status_code == 403
    assert error_code(response) == "CSRF_FAILED"


async def test_bearer_clients_are_exempt_from_csrf(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    _, session = await accounts.signed_in(as_api_client=True)

    response = await api_client.patch(
        "/api/v1/me", json={"city": "El Obour"}, headers=session.bearer_headers
    )

    assert response.status_code == 200
    assert response.json()["city"] == "El Obour"


async def test_safe_methods_do_not_require_csrf(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    await accounts.signed_in()

    assert (await api_client.get("/api/v1/me")).status_code == 200


# --- Refresh reuse (ADR-0004) -----------------------------------------------------------------


async def test_replaying_a_rotated_refresh_token_revokes_the_family(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    _, session = await accounts.signed_in(as_api_client=True)
    old = session.refresh_token
    assert old is not None

    rotated = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": old},
        headers={"X-Client-Type": "api"},
    )
    assert rotated.status_code == 200
    new = rotated.json()["refreshToken"]
    assert new != old
    # Rotation always sets cookies (browsers need them); an API-client test must not let those
    # cookies hide which token the next request actually presented.
    api_client.cookies.clear()

    replay = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": old},
        headers={"X-Client-Type": "api"},
    )
    assert replay.status_code == 401
    assert error_code(replay) == "SESSION_REVOKED"

    # The honest token of the same family is dead too — both the thief and the owner re-auth.
    honest = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": new},
        headers={"X-Client-Type": "api"},
    )
    assert honest.status_code == 401
    assert error_code(honest) == "SESSION_REVOKED"


# --- Account enumeration (BR-AUTH-03) ---------------------------------------------------------


async def test_login_failure_is_identical_for_unknown_and_wrong_password(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    credentials, _ = await accounts.signed_in()

    unknown = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": DEFAULT_PASSWORD},
    )
    wrong = await api_client.post(
        "/api/v1/auth/login",
        json={"email": credentials.email, "password": "definitely-not-the-password"},
    )

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["code"] == wrong.json()["code"] == "UNAUTHENTICATED"
    assert unknown.json()["detail"] == wrong.json()["detail"]


async def test_forgot_password_is_identical_for_unknown_addresses(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    credentials, _ = await accounts.signed_in()

    known = await api_client.post("/api/v1/auth/password/forgot", json={"email": credentials.email})
    unknown = await api_client.post(
        "/api/v1/auth/password/forgot", json={"email": "nobody@example.com"}
    )

    assert (known.status_code, known.json()) == (unknown.status_code, unknown.json())


# --- IDOR -------------------------------------------------------------------------------------


async def test_a_user_cannot_revoke_someone_elses_session(
    accounts: AccountFactory, second_accounts: AccountFactory, api_client: AsyncClient
) -> None:
    _, victim = await accounts.signed_in()
    _, attacker = await second_accounts.signed_in()

    response = await second_accounts.client.delete(
        f"/api/v1/me/sessions/{victim.session_id}", headers=attacker.csrf_headers
    )

    assert response.status_code == 404
    assert error_code(response) == "NOT_FOUND"
    assert (await api_client.post("/api/v1/auth/refresh")).status_code == 200


# --- Expired access token ---------------------------------------------------------------------


async def test_an_expired_access_token_is_reported_as_token_expired(
    accounts: AccountFactory, api_app: FastAPI, api_client: AsyncClient
) -> None:
    _, session = await accounts.signed_in(as_api_client=True)
    me = await api_client.get("/api/v1/me", headers=session.bearer_headers)
    tokens: AccessTokenService = api_app.state.access_token_service
    stale = tokens.issue(
        user_id=UUID(me.json()["id"]),
        session_id=session.session_id,
        roles=("PASSENGER",),
        token_id=session.session_id,
        issued_at=datetime.now(UTC) - timedelta(hours=2),
    )

    response = await api_client.get("/api/v1/me", headers={"Authorization": f"Bearer {stale}"})

    assert response.status_code == 401
    assert error_code(response) == "TOKEN_EXPIRED"


# --- Rate limiting (security.md §7) -----------------------------------------------------------


async def test_login_rate_limit_returns_429_with_retry_after(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    credentials, _ = await accounts.signed_in()
    last = None
    # Per-identifier default is 5 / 15 minutes; the successful login already consumed one.
    for _ in range(5):
        last = await api_client.post(
            "/api/v1/auth/login",
            json={"email": credentials.email, "password": "wrong-password-xx"},
        )
    assert last is not None
    assert last.status_code == 429
    assert error_code(last) == "RATE_LIMITED"
    assert int(last.headers["Retry-After"]) >= 1


async def test_register_rate_limit_returns_429(accounts: AccountFactory) -> None:
    last = None
    for _ in range(6):
        _, last = await accounts.register()
    assert last is not None
    assert last.status_code == 429
    assert error_code(last) == "RATE_LIMITED"
