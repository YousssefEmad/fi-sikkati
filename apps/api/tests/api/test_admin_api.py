"""Admin console: community ADMIN vs SUPER_ADMIN (FR-ADM-*)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from sqlalchemy import text

from tests.support.accounts import AccountFactory

pytestmark = pytest.mark.integration


async def _grant(api_app: FastAPI, user_id: str, role: str) -> None:
    async with api_app.state.database.session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO user_roles (user_id, role) VALUES (:id, :role) ON CONFLICT DO NOTHING"
            ),
            {"id": user_id, "role": role},
        )
        await session.commit()


async def test_admin_sees_overview_but_not_contact_pii(
    accounts: AccountFactory, second_accounts: AccountFactory, api_app: FastAPI
) -> None:
    _target, target_session = await accounts.signed_in(as_api_client=True)
    target = await accounts.client.get("/api/v1/me", headers=target_session.bearer_headers)
    target_id = target.json()["id"]
    _admin, admin_session = await second_accounts.signed_in(as_api_client=True)
    admin = await second_accounts.client.get("/api/v1/me", headers=admin_session.bearer_headers)
    await _grant(api_app, admin.json()["id"], "ADMIN")

    overview = await second_accounts.client.get(
        "/api/v1/admin/analytics/overview", headers=admin_session.bearer_headers
    )
    assert overview.status_code == 200, overview.text
    assert overview.json()["usersTotal"] >= 2

    users = await second_accounts.client.get(
        "/api/v1/admin/users", headers=admin_session.bearer_headers
    )
    assert users.status_code == 200
    assert "email" not in users.json()["items"][0]

    contact = await second_accounts.client.get(
        f"/api/v1/admin/users/{target_id}/contact", headers=admin_session.bearer_headers
    )
    assert contact.status_code == 403


async def test_super_admin_can_read_contact_and_flags(
    accounts: AccountFactory, second_accounts: AccountFactory, api_app: FastAPI
) -> None:
    _target, target_session = await accounts.signed_in(as_api_client=True)
    target = await accounts.client.get("/api/v1/me", headers=target_session.bearer_headers)
    _owner, owner_session = await second_accounts.signed_in(as_api_client=True)
    owner = await second_accounts.client.get("/api/v1/me", headers=owner_session.bearer_headers)
    await _grant(api_app, owner.json()["id"], "SUPER_ADMIN")

    contact = await second_accounts.client.get(
        f"/api/v1/admin/users/{target.json()['id']}/contact",
        headers=owner_session.bearer_headers,
    )
    assert contact.status_code == 200, contact.text
    assert "@" in contact.json()["email"]

    flags = await second_accounts.client.get(
        "/api/v1/admin/feature-flags", headers=owner_session.bearer_headers
    )
    assert flags.status_code == 200, flags.text
    keys = {item["key"] for item in flags.json()["items"]}
    assert "ai.enabled" in keys

    settings = await second_accounts.client.put(
        "/api/v1/admin/feature-flags/ai.enabled",
        json={"enabled": True},
        headers=owner_session.bearer_headers,
    )
    assert settings.status_code == 200
    assert settings.json()["enabled"] is True

    asked = await second_accounts.client.post(
        "/api/v1/ai/assistant",
        json={"message": "how does this work?"},
        headers=owner_session.bearer_headers,
    )
    assert asked.status_code == 200, asked.text
    assert "taxi" in asked.json()["answer"].lower()


async def test_admin_cannot_grant_super_admin(
    accounts: AccountFactory, second_accounts: AccountFactory, api_app: FastAPI
) -> None:
    _target, target_session = await accounts.signed_in(as_api_client=True)
    target = await accounts.client.get("/api/v1/me", headers=target_session.bearer_headers)
    _owner, owner_session = await second_accounts.signed_in(as_api_client=True)
    owner = await second_accounts.client.get("/api/v1/me", headers=owner_session.bearer_headers)
    await _grant(api_app, owner.json()["id"], "SUPER_ADMIN")
    forbidden = await second_accounts.client.put(
        f"/api/v1/admin/users/{target.json()['id']}/roles",
        json={"roles": ["SUPER_ADMIN"]},
        headers=owner_session.bearer_headers,
    )
    assert forbidden.status_code in {400, 403, 422}
