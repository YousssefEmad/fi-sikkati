"""Account and profile endpoints (BR-ACC-*)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.support.accounts import AccountFactory
from tests.support.http import error_code

pytestmark = pytest.mark.integration


async def test_get_me_returns_the_owner_record(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    credentials, _ = await accounts.signed_in(
        displayName="سارة", fullName="Sara Test", locale="ar", phone="+201001234567"
    )

    response = await api_client.get("/api/v1/me")

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == credentials.email
    assert body["displayName"] == "سارة"
    assert body["fullName"] == "Sara Test"
    assert body["phone"] == "+201001234567"
    assert body["roles"] == ["PASSENGER"]
    assert body["status"] == "ACTIVE"
    assert body["identityVerificationStatus"] == "NOT_SUBMITTED"
    assert "password" not in body
    assert "passwordHash" not in body


async def test_patch_me_updates_only_the_fields_that_were_sent(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    _, session = await accounts.signed_in(displayName="Original", locale="en")

    response = await api_client.patch(
        "/api/v1/me",
        json={"displayName": "Updated", "city": "El Obour", "locale": "ar"},
        headers=session.csrf_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["displayName"] == "Updated"
    assert body["city"] == "El Obour"
    assert body["locale"] == "ar"
    assert body["fullName"] == "Test Passenger"


async def test_patch_me_rejects_a_phone_number_another_account_holds(
    accounts: AccountFactory, second_accounts: AccountFactory
) -> None:
    await accounts.signed_in(phone="+201001111111")
    _, other = await second_accounts.signed_in()

    taken = await second_accounts.client.patch(
        "/api/v1/me", json={"phone": "+201001111111"}, headers=other.csrf_headers
    )

    assert taken.status_code == 409
    assert error_code(taken) == "PHONE_TAKEN"


async def test_delete_me_closes_the_account_and_ends_the_session(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    _, session = await accounts.signed_in()

    response = await api_client.delete("/api/v1/me", headers=session.csrf_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "DELETED"
    assert body["anonymisedAfter"]
    assert (await api_client.get("/api/v1/me")).status_code == 401
    assert (await api_client.post("/api/v1/auth/refresh")).status_code == 401


async def test_public_profile_hides_private_fields(
    accounts: AccountFactory, second_accounts: AccountFactory, api_client: AsyncClient
) -> None:
    _, session = await accounts.signed_in(displayName="Public Name")
    patched = await api_client.patch(
        "/api/v1/me", json={"city": "El Obour"}, headers=session.csrf_headers
    )
    assert patched.status_code == 200
    owner_id = patched.json()["id"]
    await second_accounts.signed_in()

    response = await second_accounts.client.get(f"/api/v1/users/{owner_id}/public-profile")

    assert response.status_code == 200
    body = response.json()
    assert body["displayName"] == "Public Name"
    assert body["city"] == "El Obour"
    assert body["isDriver"] is False
    assert body["identityVerified"] is False
    assert body["photoUrl"] is None
    assert "email" not in body
    assert "phone" not in body
    assert "fullName" not in body


async def test_public_profile_of_an_unknown_user_is_not_found(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    await accounts.signed_in()

    response = await api_client.get(f"/api/v1/users/{uuid4()}/public-profile")

    assert response.status_code == 404
    assert error_code(response) == "NOT_FOUND"


async def test_deleted_accounts_have_no_public_profile(
    accounts: AccountFactory,
    second_accounts: AccountFactory,
    api_client: AsyncClient,
) -> None:
    _, session = await accounts.signed_in()
    owner_id = (await api_client.get("/api/v1/me")).json()["id"]
    await second_accounts.signed_in()
    await api_client.delete("/api/v1/me", headers=session.csrf_headers)

    response = await second_accounts.client.get(f"/api/v1/users/{owner_id}/public-profile")

    assert response.status_code == 404


async def test_patch_me_rejects_a_blank_display_name(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    _, session = await accounts.signed_in()

    response = await api_client.patch(
        "/api/v1/me", json={"displayName": "  "}, headers=session.csrf_headers
    )

    assert response.status_code == 400
    assert error_code(response) == "VALIDATION_ERROR"
