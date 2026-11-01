"""End-to-end authentication flows against a real database (BR-AUTH-01 … BR-AUTH-09).

Everything goes through HTTP, because the rules these tests protect are only correct as a whole:
the cookie attributes matter as much as the row in ``auth_sessions``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.security import (
    ACCESS_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    REFRESH_COOKIE_PATH,
)
from tests.support.accounts import DEFAULT_PASSWORD, AccountFactory, adult_date_of_birth
from tests.support.email import RecordingEmailSender
from tests.support.http import error_code, field_errors, set_cookies

pytestmark = pytest.mark.integration

NEW_PASSWORD = "an-entirely-different-passphrase"


# --- registration and email verification ------------------------------------------------------


async def test_registration_is_accepted_and_sends_a_verification_link(
    accounts: AccountFactory, sent_emails: RecordingEmailSender
) -> None:
    credentials, response = await accounts.register(locale="en")

    assert response.status_code == 202
    assert response.json() == {"status": "ACCEPTED"}
    message = sent_emails.last_for(credentials.email)
    assert "Confirm" in message.subject
    assert "/en/auth/verify-email?token=" in message.text_body
    assert sent_emails.token_for(credentials.email)


async def test_registration_email_follows_the_chosen_locale(
    accounts: AccountFactory, sent_emails: RecordingEmailSender
) -> None:
    credentials, response = await accounts.register(locale="ar")

    assert response.status_code == 202
    message = sent_emails.last_for(credentials.email)
    assert "في سكتي" in message.subject
    assert '<html lang="ar" dir="rtl">' in message.html_body


async def test_br_auth_03_registering_a_known_address_is_indistinguishable(
    accounts: AccountFactory, sent_emails: RecordingEmailSender
) -> None:
    """The response must never reveal that an address is already registered."""
    credentials, first = await accounts.register(locale="en")
    _, second = await accounts.register(email=credentials.email, locale="en")

    assert (first.status_code, first.json()) == (second.status_code, second.json())
    # Only the email differs: the second one is a "someone tried to register" notice with no
    # verification token in it.
    messages = sent_emails.all_for(credentials.email)
    assert len(messages) == 2
    assert "token=" not in messages[1].text_body


async def test_email_verification_is_single_use(
    accounts: AccountFactory, api_client: AsyncClient, sent_emails: RecordingEmailSender
) -> None:
    credentials, _ = await accounts.register()
    token = sent_emails.token_for(credentials.email)

    first = await api_client.post("/api/v1/auth/email/verify", json={"token": token})
    second = await api_client.post("/api/v1/auth/email/verify", json={"token": token})

    assert first.status_code == 204
    assert second.status_code == 400
    assert error_code(second) == "INVALID_TOKEN"


async def test_unknown_verification_token_is_rejected(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/v1/auth/email/verify", json={"token": "x" * 43})
    assert response.status_code == 400
    assert error_code(response) == "INVALID_TOKEN"


async def test_resending_a_verification_email_issues_a_fresh_token(
    accounts: AccountFactory, api_client: AsyncClient, sent_emails: RecordingEmailSender
) -> None:
    credentials, _ = await accounts.register()
    first_token = sent_emails.token_for(credentials.email)

    response = await api_client.post("/api/v1/auth/email/resend", json={"email": credentials.email})
    second_token = sent_emails.token_for(credentials.email)

    assert response.status_code == 202
    assert second_token != first_token
    # Issuing a new link retires the previous unused one, so an intercepted older mail is dead.
    stale = await api_client.post("/api/v1/auth/email/verify", json={"token": first_token})
    assert stale.status_code == 400
    assert (
        await api_client.post("/api/v1/auth/email/verify", json={"token": second_token})
    ).status_code == 204


async def test_resending_to_an_unknown_address_reveals_nothing(
    api_client: AsyncClient, sent_emails: RecordingEmailSender
) -> None:
    response = await api_client.post(
        "/api/v1/auth/email/resend", json={"email": "nobody@example.com"}
    )
    assert response.status_code == 202
    assert sent_emails.all_for("nobody@example.com") == []


async def test_registration_rejects_a_minor(accounts: AccountFactory) -> None:
    """BR-ACC-08 / OD-022: the minimum age is 18."""
    _, response = await accounts.register(dateOfBirth=adult_date_of_birth(16).isoformat())

    assert response.status_code == 400
    assert error_code(response) == "VALIDATION_ERROR"
    assert field_errors(response) == {"dateOfBirth": "MINIMUM_AGE"}


async def test_registration_rejects_a_future_date_of_birth(accounts: AccountFactory) -> None:
    tomorrow = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
    _, response = await accounts.register(dateOfBirth=tomorrow)

    assert response.status_code == 400
    assert field_errors(response) == {"dateOfBirth": "INVALID"}


async def test_registration_rejects_outdated_legal_versions(accounts: AccountFactory) -> None:
    """BR-ACC-08: the user must accept the documents currently published."""
    _, response = await accounts.register(acceptedTermsVersion="1999-01-01")

    assert response.status_code == 409
    assert error_code(response) == "LEGAL_VERSION_MISMATCH"


async def test_registration_rejects_a_short_password(accounts: AccountFactory) -> None:
    _, response = await accounts.register(password="short")

    assert response.status_code == 400
    assert field_errors(response) == {"password": "LENGTH"}


async def test_registration_rejects_a_malformed_phone_number(accounts: AccountFactory) -> None:
    _, response = await accounts.register(phone="01001234567")

    assert response.status_code == 400
    assert "phone" in field_errors(response)


async def test_registration_rejects_unknown_fields(api_client: AsyncClient) -> None:
    """security.md §5: ``extra="forbid"`` stops mass assignment."""
    response = await api_client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": DEFAULT_PASSWORD, "status": "ACTIVE"},
    )
    assert response.status_code == 400
    assert error_code(response) == "VALIDATION_ERROR"


# --- sign in ----------------------------------------------------------------------------------


async def test_login_sets_hardened_session_cookies(accounts: AccountFactory) -> None:
    """ADR-0004: prefixed, HttpOnly, Secure, SameSite=Lax; the refresh cookie is path-scoped."""
    credentials, _ = await accounts.register()
    await accounts.verify_email(credentials.email)
    session, response = await accounts.login(credentials)

    assert session is not None
    assert response.status_code == 200
    cookies = set_cookies(response)
    assert set(cookies) == {ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME, CSRF_COOKIE_NAME}

    for name in (ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME):
        cookie = cookies[name]
        assert "httponly" in cookie, name
        assert "secure" in cookie, name
        assert cookie["samesite"].lower() == "lax", name

    assert cookies[ACCESS_COOKIE_NAME]["path"] == "/"
    assert cookies[REFRESH_COOKIE_NAME]["path"] == REFRESH_COOKIE_PATH
    # The CSRF cookie is the only one the page's JavaScript must be able to read.
    assert "httponly" not in cookies[CSRF_COOKIE_NAME]
    assert "secure" in cookies[CSRF_COOKIE_NAME]


async def test_browsers_do_not_receive_tokens_in_the_body(accounts: AccountFactory) -> None:
    credentials, _ = await accounts.register()
    session, response = await accounts.login(credentials)

    assert session is not None
    assert response.json()["accessToken"] is None
    assert response.json()["refreshToken"] is None
    assert session.csrf_token


async def test_api_clients_receive_tokens_in_the_body(accounts: AccountFactory) -> None:
    credentials, _ = await accounts.register()
    session, _ = await accounts.login(credentials, as_api_client=True)

    assert session is not None
    assert session.access_token
    assert session.refresh_token


async def test_login_before_verification_works_but_me_shows_it(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    """BR-AUTH-05: confirming the address gates joining trips, not signing in."""
    credentials, _ = await accounts.register()
    session, _ = await accounts.login(credentials)
    assert session is not None

    me = await api_client.get("/api/v1/me")
    assert me.status_code == 200
    assert me.json()["emailVerified"] is False


async def test_verification_shows_up_on_me(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    await accounts.signed_in()
    me = await api_client.get("/api/v1/me")

    assert me.status_code == 200
    assert me.json()["emailVerified"] is True
    assert me.json()["roles"] == ["PASSENGER"]


# --- refresh rotation -------------------------------------------------------------------------


async def test_refresh_rotates_the_token_for_api_clients(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    _, session = await accounts.signed_in(as_api_client=True)

    rotated = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": session.refresh_token},
        headers={"X-Client-Type": "api"},
    )

    assert rotated.status_code == 200
    body = rotated.json()
    assert body["refreshToken"] != session.refresh_token
    assert body["accessToken"]
    # rotate() inserts a new row in the same family; the previous refresh token is the tripwire.
    replay = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": session.refresh_token},
        headers={"X-Client-Type": "api"},
    )
    assert replay.status_code == 401


async def test_refresh_works_from_the_cookie_alone(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    await accounts.signed_in()
    before = api_client.cookies[REFRESH_COOKIE_NAME]

    response = await api_client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    assert api_client.cookies[REFRESH_COOKIE_NAME] != before


async def test_refresh_without_any_token_is_unauthenticated(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert error_code(response) == "UNAUTHENTICATED"


# --- sign out ---------------------------------------------------------------------------------


async def test_br_auth_09_logout_revokes_the_session_and_clears_cookies(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    _, session = await accounts.signed_in()

    response = await api_client.post("/api/v1/auth/logout", headers=session.csrf_headers)

    assert response.status_code == 204
    assert ACCESS_COOKIE_NAME not in api_client.cookies
    assert REFRESH_COOKIE_NAME not in api_client.cookies
    # The session is gone server-side, so it can never be refreshed again (BR-AUTH-08 allows
    # reads to keep working until the short-lived access token expires).
    refresh = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": session.refresh_token},
    )
    assert refresh.status_code == 401


async def test_logout_is_idempotent(accounts: AccountFactory, api_client: AsyncClient) -> None:
    _, session = await accounts.signed_in(as_api_client=True)
    headers = {**session.csrf_headers, **session.bearer_headers}

    first = await api_client.post("/api/v1/auth/logout", headers=headers)
    second = await api_client.post("/api/v1/auth/logout", headers=headers)

    assert first.status_code == 204
    assert second.status_code == 204


# --- password reset and change ----------------------------------------------------------------


async def test_br_auth_06_password_reset_replaces_the_password_and_revokes_sessions(
    accounts: AccountFactory,
    api_client: AsyncClient,
    second_client: AsyncClient,
    sent_emails: RecordingEmailSender,
) -> None:
    credentials, session = await accounts.signed_in()

    requested = await api_client.post(
        "/api/v1/auth/password/forgot", json={"email": credentials.email}
    )
    assert requested.status_code == 202
    token = sent_emails.token_for(credentials.email)

    reset = await second_client.post(
        "/api/v1/auth/password/reset", json={"token": token, "newPassword": NEW_PASSWORD}
    )
    assert reset.status_code == 204

    # The old password is dead, the new one works, and the session from before is revoked.
    old, _ = await accounts.login(credentials)
    assert old is None
    refreshed = await api_client.post(
        "/api/v1/auth/refresh", json={"refreshToken": session.refresh_token}
    )
    assert refreshed.status_code == 401

    new_session, response = await accounts.login(
        type(credentials)(email=credentials.email, password=NEW_PASSWORD)
    )
    assert new_session is not None, response.text
    # BR-AUTH-06 also tells the user their password changed.
    assert any("password" in m.subject.lower() for m in sent_emails.all_for(credentials.email))


async def test_password_reset_token_is_single_use(
    accounts: AccountFactory, api_client: AsyncClient, sent_emails: RecordingEmailSender
) -> None:
    credentials, _ = await accounts.signed_in()
    await api_client.post("/api/v1/auth/password/forgot", json={"email": credentials.email})
    token = sent_emails.token_for(credentials.email)

    first = await api_client.post(
        "/api/v1/auth/password/reset", json={"token": token, "newPassword": NEW_PASSWORD}
    )
    second = await api_client.post(
        "/api/v1/auth/password/reset", json={"token": token, "newPassword": NEW_PASSWORD}
    )

    assert first.status_code == 204
    assert second.status_code == 400
    assert error_code(second) == "INVALID_TOKEN"


async def test_password_reset_enforces_the_length_policy(
    accounts: AccountFactory, api_client: AsyncClient, sent_emails: RecordingEmailSender
) -> None:
    credentials, _ = await accounts.signed_in()
    await api_client.post("/api/v1/auth/password/forgot", json={"email": credentials.email})
    token = sent_emails.token_for(credentials.email)

    response = await api_client.post(
        "/api/v1/auth/password/reset", json={"token": token, "newPassword": "short"}
    )

    assert response.status_code == 400
    assert field_errors(response) == {"newPassword": "LENGTH"}


async def test_br_auth_07_password_change_needs_the_current_password(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    _, session = await accounts.signed_in()

    response = await api_client.post(
        "/api/v1/auth/password/change",
        json={"currentPassword": "not-the-password", "newPassword": NEW_PASSWORD},
        headers=session.csrf_headers,
    )

    assert response.status_code == 400
    assert field_errors(response) == {"currentPassword": "INVALID"}


async def test_br_auth_07_password_change_keeps_this_session_and_ends_the_others(
    accounts: AccountFactory,
    second_accounts: AccountFactory,
    api_client: AsyncClient,
    second_client: AsyncClient,
) -> None:
    credentials, first = await accounts.signed_in()
    other, response = await second_accounts.login(credentials)
    assert other is not None, response.text

    changed = await api_client.post(
        "/api/v1/auth/password/change",
        json={"currentPassword": credentials.password, "newPassword": NEW_PASSWORD},
        headers=first.csrf_headers,
    )
    assert changed.status_code == 204

    # This device still works…
    assert (await api_client.get("/api/v1/me")).status_code == 200
    assert (await api_client.post("/api/v1/auth/refresh")).status_code == 200
    # …the other device cannot refresh any more.
    assert (await second_client.post("/api/v1/auth/refresh")).status_code == 401
    del first, other


# --- session management -----------------------------------------------------------------------


async def test_br_auth_08_sessions_list_marks_the_current_device(
    accounts: AccountFactory,
    second_accounts: AccountFactory,
    api_client: AsyncClient,
) -> None:
    credentials, session = await accounts.signed_in()
    other, _ = await second_accounts.login(credentials)
    assert other is not None

    response = await api_client.get("/api/v1/me/sessions")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    current = [item for item in items if item["current"]]
    assert [item["id"] for item in current] == [str(session.session_id)]
    # The address itself is never shown — only a short fingerprint of its keyed hash.
    assert all(item["ipFingerprint"] is None or len(item["ipFingerprint"]) == 12 for item in items)


async def test_br_auth_08_revoking_a_device_ends_its_session(
    accounts: AccountFactory,
    second_accounts: AccountFactory,
    api_client: AsyncClient,
    second_client: AsyncClient,
) -> None:
    credentials, session = await accounts.signed_in()
    other, _ = await second_accounts.login(credentials)
    assert other is not None

    revoked = await api_client.delete(
        f"/api/v1/me/sessions/{other.session_id}", headers=session.csrf_headers
    )

    assert revoked.status_code == 204
    assert (await second_client.post("/api/v1/auth/refresh")).status_code == 401
    assert (await api_client.post("/api/v1/auth/refresh")).status_code == 200


async def test_revoking_an_unknown_session_is_not_found(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    _, session = await accounts.signed_in()

    response = await api_client.delete(
        f"/api/v1/me/sessions/{uuid4()}",
        headers=session.csrf_headers,
    )

    assert response.status_code == 404
    assert error_code(response) == "NOT_FOUND"


# --- deletion grace period --------------------------------------------------------------------


async def test_br_acc_07_signing_in_during_the_grace_period_restores_the_account(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    credentials, session = await accounts.signed_in()

    deleted = await api_client.delete("/api/v1/me", headers=session.csrf_headers)
    assert deleted.status_code == 200

    restored, response = await accounts.login(credentials)
    assert restored is not None, response.text
    me = await api_client.get("/api/v1/me")
    assert me.json()["status"] == "ACTIVE"
    assert me.json()["deletionRequestedAt"] is None
