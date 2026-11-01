"""Password hashing, opaque tokens, access tokens and CSRF (security.md §1)."""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.ids import uuid7
from app.core.security import (
    AccessTokenService,
    ExpiredTokenError,
    PasswordService,
    TokenError,
    generate_opaque_token,
    hash_opaque_token,
    issue_csrf_token,
    keyed_hash,
    verify_csrf_token,
)

PASSWORD = "a-perfectly-fine-passphrase"


def test_password_hash_is_salted_and_verifiable(settings: Settings) -> None:
    passwords = PasswordService(settings)
    first = passwords.hash(PASSWORD)
    second = passwords.hash(PASSWORD)

    assert first != second, "each hash must use a fresh salt"
    assert first.startswith("$argon2id$")
    assert passwords.verify(first, PASSWORD)
    assert passwords.verify(second, PASSWORD)
    assert not passwords.verify(first, PASSWORD + "x")


def test_password_verification_fails_without_the_pepper(settings: Settings) -> None:
    """A stolen hash is useless to anyone who does not also have the server pepper."""
    stored = PasswordService(settings).hash(PASSWORD)
    other_pepper = settings.model_copy(update={"auth_password_pepper": settings.auth_csrf_secret})

    assert not PasswordService(other_pepper).verify(stored, PASSWORD)


def test_password_verify_rejects_a_malformed_hash(settings: Settings) -> None:
    assert not PasswordService(settings).verify("not-a-hash", PASSWORD)


def test_needs_rehash_detects_weaker_parameters(settings: Settings) -> None:
    weak = settings.model_copy(update={"argon2_memory_cost_kib": 8192})
    strong = settings.model_copy(update={"argon2_memory_cost_kib": 16384})
    stored = PasswordService(weak).hash(PASSWORD)

    assert PasswordService(strong).needs_rehash(stored)
    assert not PasswordService(weak).needs_rehash(stored)


def test_opaque_tokens_are_unique_and_only_stored_hashed() -> None:
    tokens = {generate_opaque_token() for _ in range(100)}
    assert len(tokens) == 100

    token = tokens.pop()
    digest = hash_opaque_token(token)
    assert len(digest) == 64
    assert token not in digest
    assert hash_opaque_token(token) == digest


def test_keyed_hash_depends_on_the_secret() -> None:
    assert keyed_hash("1.2.3.4", "secret-a") != keyed_hash("1.2.3.4", "secret-b")
    assert keyed_hash("1.2.3.4", "secret-a") == keyed_hash("1.2.3.4", "secret-a")


def test_access_token_round_trip(settings: Settings) -> None:
    tokens = AccessTokenService(settings)
    user_id, session_id, token_id = uuid7(), uuid7(), uuid7()
    issued_at = datetime.now(UTC)

    claims = tokens.verify(
        tokens.issue(
            user_id=user_id,
            session_id=session_id,
            roles=("PASSENGER",),
            token_id=token_id,
            issued_at=issued_at,
        )
    )

    assert claims.user_id == user_id
    assert claims.session_id == session_id
    assert claims.roles == ("PASSENGER",)
    assert claims.token_id == token_id
    assert claims.expires_at - claims.issued_at == tokens.ttl


def test_expired_access_token_is_rejected(settings: Settings) -> None:
    tokens = AccessTokenService(settings)
    long_ago = datetime.now(UTC) - timedelta(days=1)
    token = tokens.issue(
        user_id=uuid7(),
        session_id=uuid7(),
        roles=(),
        token_id=uuid7(),
        issued_at=long_ago,
    )

    with pytest.raises(ExpiredTokenError):
        tokens.verify(token)


def test_tampered_access_token_is_rejected(settings: Settings) -> None:
    tokens = AccessTokenService(settings)
    token = tokens.issue(
        user_id=uuid7(),
        session_id=uuid7(),
        roles=("PASSENGER",),
        token_id=uuid7(),
        issued_at=datetime.now(UTC),
    )
    header, payload, signature = token.split(".")
    # Swap two characters of the signature: it can no longer verify.
    tampered = f"{header}.{payload}.{signature[1]}{signature[0]}{signature[2:]}"

    with pytest.raises(TokenError):
        tokens.verify(tampered)


def test_token_signed_by_another_key_is_rejected(settings: Settings) -> None:
    other_seed = SecretStr(base64.b64encode(b"a-completely-different-seed-32by").decode())
    other = AccessTokenService(settings.model_copy(update={"auth_jwt_private_key": other_seed}))
    token = other.issue(
        user_id=uuid7(),
        session_id=uuid7(),
        roles=(),
        token_id=uuid7(),
        issued_at=datetime.now(UTC),
    )

    with pytest.raises(TokenError):
        AccessTokenService(settings).verify(token)


def test_csrf_token_is_bound_to_the_session(settings: Settings) -> None:
    secret = settings.auth_csrf_secret.get_secret_value()
    session_id, other_session = uuid7(), uuid7()
    token = issue_csrf_token(session_id, secret)

    assert verify_csrf_token(token, session_id, secret)
    assert not verify_csrf_token(token, other_session, secret)
    assert not verify_csrf_token(None, session_id, secret)
    assert not verify_csrf_token("", session_id, secret)
