"""Cryptographic primitives: password hashing, access-token signing, opaque tokens, CSRF.

Everything secret-dependent is created from :class:`~app.core.config.Settings` so nothing reads
the environment at import time and tests can use cheap parameters. This module knows nothing
about the database or HTTP routing — see ``app.core.authz`` for enforcement and
``app.modules.auth`` for the flows (ADR-0004, security.md §1).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Final
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from app.core.config import Settings

# --- Transport constants (ADR-0004) ------------------------------------------------------------
# ``__Host-`` requires Secure + Path=/ + no Domain; the refresh cookie needs a narrower path, so
# it carries the ``__Secure-`` prefix instead. Both require HTTPS (localhost counts as secure).
ACCESS_COOKIE_NAME: Final = "__Host-fs_access"
REFRESH_COOKIE_NAME: Final = "__Secure-fs_refresh"
CSRF_COOKIE_NAME: Final = "__Host-fs_csrf"
CSRF_HEADER_NAME: Final = "X-CSRF-Token"
REFRESH_COOKIE_PATH: Final = "/api/v1/auth/refresh"

# S105 is suppressed on the next three lines: the rule flags any constant whose name contains
# "token", and these are the JWT algorithm, issuer and audience — all public values.
ACCESS_TOKEN_ALGORITHM: Final = "EdDSA"  # noqa: S105
ACCESS_TOKEN_ISSUER: Final = "fi-sikkati"  # noqa: S105
ACCESS_TOKEN_AUDIENCE: Final = "fi-sikkati-api"  # noqa: S105
# Tolerated clock skew when validating ``exp``/``iat`` (security.md §8).
CLOCK_SKEW_SECONDS: Final = 30

OPAQUE_TOKEN_BYTES: Final = 32
_ED25519_SEED_BYTES: Final = 32
PASSWORD_MAX_LENGTH: Final = 128


class TokenError(Exception):
    """Raised when an access token cannot be verified."""


class ExpiredTokenError(TokenError):
    """Raised when an access token is well-formed but past its expiry."""


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """Verified claims of an access token (ADR-0004: ``sub``, ``sid``, ``roles``, ``jti``)."""

    user_id: UUID
    session_id: UUID
    roles: tuple[str, ...]
    token_id: UUID
    issued_at: datetime
    expires_at: datetime


# --- Passwords --------------------------------------------------------------------------------


def _decode_base64(value: str, *, field: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(padded.replace("+", "-").replace("/", "_"))
    except (ValueError, TypeError) as exc:
        msg = f"{field} must be valid base64"
        raise ValueError(msg) from exc


@lru_cache(maxsize=4)
def _password_hasher(time_cost: int, memory_cost_kib: int, parallelism: int) -> PasswordHasher:
    return PasswordHasher(
        time_cost=time_cost,
        memory_cost=memory_cost_kib,
        parallelism=parallelism,
        hash_len=32,
        salt_len=16,
    )


def _peppered(password: str, pepper: str) -> bytes:
    """HMAC the password with the server pepper before hashing (security.md §1).

    A stolen database is useless without the pepper, which lives in the secret store and never in
    PostgreSQL. HMAC also bounds the input length that Argon2 sees.
    """
    return hmac.new(pepper.encode("utf-8"), password.encode("utf-8"), hashlib.sha256).digest()


class PasswordService:
    """Hash and verify passwords with Argon2id over a peppered input."""

    def __init__(self, settings: Settings) -> None:
        self._hasher = _password_hasher(
            settings.argon2_time_cost,
            settings.argon2_memory_cost_kib,
            settings.argon2_parallelism,
        )
        self._pepper = settings.auth_password_pepper.get_secret_value()

    def hash(self, password: str) -> str:
        return self._hasher.hash(_peppered(password, self._pepper))

    def verify(self, password_hash: str, password: str) -> bool:
        """Return whether the password matches. Never raises on a wrong password."""
        try:
            return self._hasher.verify(password_hash, _peppered(password, self._pepper))
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        """True when the stored hash used weaker parameters than the current configuration."""
        try:
            return self._hasher.check_needs_rehash(password_hash)
        except InvalidHashError:
            return True

    def dummy_verify(self) -> None:
        """Burn one Argon2 computation so responses take the same time for unknown accounts.

        Login must not leak whether an email exists through timing (security.md §1). Hashing a
        constant costs the same as verifying a stored hash with the same parameters.
        """
        self._hasher.hash(_peppered(_TIMING_EQUALISER_INPUT, self._pepper))


_TIMING_EQUALISER_INPUT: Final = "fi-sikkati-timing-equaliser"


# --- Opaque tokens (refresh sessions, email verification, password reset) ----------------------


def generate_opaque_token() -> str:
    """Return a 256-bit URL-safe random token. Only its SHA-256 hash is ever stored."""
    return secrets.token_urlsafe(OPAQUE_TOKEN_BYTES)


def hash_opaque_token(token: str) -> str:
    """Hash a bearer-style token for storage/lookup.

    SHA-256 without a salt is correct here (unlike for passwords): the input is 256 bits of
    entropy, so brute force is infeasible, and lookups must be possible by hash.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_equal(left: str, right: str) -> bool:
    """Timing-safe comparison for secrets (security.md §8)."""
    return hmac.compare_digest(left, right)


def keyed_hash(value: str, secret: str) -> str:
    """Keyed hash for values that must be correlatable but never readable (IPs, identifiers)."""
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


# --- Access tokens ----------------------------------------------------------------------------


class AccessTokenService:
    """Sign and verify Ed25519-signed access tokens with ``kid``-based key rotation."""

    def __init__(self, settings: Settings) -> None:
        seed = _decode_base64(
            settings.auth_jwt_private_key.get_secret_value(), field="AUTH_JWT_PRIVATE_KEY"
        )
        if len(seed) != _ED25519_SEED_BYTES:
            msg = "AUTH_JWT_PRIVATE_KEY must decode to a 32-byte Ed25519 seed"
            raise ValueError(msg)
        self._active_kid = settings.auth_jwt_active_kid
        self._private_key = Ed25519PrivateKey.from_private_bytes(seed)
        self._public_keys: dict[str, Ed25519PublicKey] = {
            self._active_kid: self._private_key.public_key()
        }
        for kid, encoded in settings.auth_jwt_retired_public_keys.items():
            self._public_keys[kid] = Ed25519PublicKey.from_public_bytes(
                _decode_base64(encoded, field="AUTH_JWT_RETIRED_PUBLIC_KEYS")
            )
        self._ttl = timedelta(seconds=settings.auth_access_token_ttl_seconds)

    @property
    def ttl(self) -> timedelta:
        return self._ttl

    def issue(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        roles: tuple[str, ...],
        token_id: UUID,
        issued_at: datetime,
    ) -> str:
        expires_at = issued_at + self._ttl
        return jwt.encode(
            {
                "iss": ACCESS_TOKEN_ISSUER,
                "aud": ACCESS_TOKEN_AUDIENCE,
                "sub": str(user_id),
                "sid": str(session_id),
                "roles": list(roles),
                "jti": str(token_id),
                "iat": int(issued_at.timestamp()),
                "exp": int(expires_at.timestamp()),
            },
            self._private_key,
            algorithm=ACCESS_TOKEN_ALGORITHM,
            headers={"kid": self._active_kid},
        )

    def verify(self, token: str) -> AccessTokenClaims:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise TokenError(str(exc)) from exc

        public_key = self._public_keys.get(str(header.get("kid", "")))
        if public_key is None:
            msg = "unknown signing key"
            raise TokenError(msg)

        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[ACCESS_TOKEN_ALGORITHM],
                issuer=ACCESS_TOKEN_ISSUER,
                audience=ACCESS_TOKEN_AUDIENCE,
                leeway=CLOCK_SKEW_SECONDS,
                options={"require": ["sub", "sid", "jti", "iat", "exp"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise ExpiredTokenError(str(exc)) from exc
        except jwt.PyJWTError as exc:
            raise TokenError(str(exc)) from exc

        try:
            return AccessTokenClaims(
                user_id=UUID(payload["sub"]),
                session_id=UUID(payload["sid"]),
                roles=tuple(str(role) for role in payload.get("roles", ())),
                token_id=UUID(payload["jti"]),
                issued_at=datetime.fromtimestamp(int(payload["iat"]), tz=UTC),
                expires_at=datetime.fromtimestamp(int(payload["exp"]), tz=UTC),
            )
        except (KeyError, TypeError, ValueError) as exc:
            msg = "malformed token claims"
            raise TokenError(msg) from exc


# --- CSRF -------------------------------------------------------------------------------------


def issue_csrf_token(session_id: UUID, secret: str) -> str:
    """Derive the double-submit CSRF token for a session (ADR-0004).

    Binding the token to ``sid`` means a token stolen from one session cannot be replayed in
    another, and the server needs no extra storage to validate it.
    """
    return keyed_hash(f"csrf:{session_id}", secret)


def verify_csrf_token(candidate: str | None, session_id: UUID, secret: str) -> bool:
    if not candidate:
        return False
    return tokens_equal(candidate, issue_csrf_token(session_id, secret))
