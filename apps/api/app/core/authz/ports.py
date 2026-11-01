"""Ports the authorization layer needs from the module that owns identity data.

``app.core`` must not import ``app.modules`` (import-linter contract), but resolving a request's
principal needs the caller's current roles and status, and some account operations must revoke
sessions. Both are expressed here as protocols; ``app.main`` is the composition root that binds
the implementations from ``app.modules.users`` / ``app.modules.auth`` onto ``app.state``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz.permissions import Role


@dataclass(frozen=True, slots=True)
class IdentitySnapshot:
    """The authorization-relevant state of an account, read fresh per request."""

    roles: frozenset[Role]
    is_active: bool
    email_verified: bool
    phone_verified: bool


class IdentityLoader(Protocol):
    """Loads the current identity snapshot for a user id, or ``None`` if there is no such user."""

    async def __call__(self, db: AsyncSession, user_id: UUID) -> IdentitySnapshot | None: ...


class SessionRevoker(Protocol):
    """Revokes every refresh session of a user, used by account-level operations."""

    async def __call__(self, db: AsyncSession, user_id: UUID, reason: str) -> int: ...


_IDENTITY_LOADER_ATTR = "identity_loader"
_SESSION_REVOKER_ATTR = "session_revoker"


def bind_identity_loader(app_state: object, loader: IdentityLoader) -> None:
    setattr(app_state, _IDENTITY_LOADER_ATTR, loader)


def bind_session_revoker(app_state: object, revoker: SessionRevoker) -> None:
    setattr(app_state, _SESSION_REVOKER_ATTR, revoker)


def get_identity_loader(request: Request) -> IdentityLoader:
    loader = getattr(request.app.state, _IDENTITY_LOADER_ATTR, None)
    if loader is None:  # pragma: no cover — wiring error, caught by the first authed request
        msg = "No identity loader is bound; app.main must call bind_identity_loader()"
        raise RuntimeError(msg)
    return loader  # type: ignore[no-any-return]


def get_session_revoker(request: Request) -> SessionRevoker:
    revoker = getattr(request.app.state, _SESSION_REVOKER_ATTR, None)
    if revoker is None:  # pragma: no cover — wiring error
        msg = "No session revoker is bound; app.main must call bind_session_revoker()"
        raise RuntimeError(msg)
    return revoker  # type: ignore[no-any-return]
