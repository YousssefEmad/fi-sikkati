"""Roles and permissions, defined in code (ADR-0005).

This module is the executable mirror of `permission-matrix.md`. Adding a capability is a code
change that goes through review and the matrix tests in ``tests/authz/`` — permissions are
deliberately **not** stored in the database, because a row update must never be able to grant
privileges without review.

Only permissions whose endpoints exist are listed. Later phases add their own entries together
with the routes that enforce them; the matrix test asserts that every declared permission is
reachable and that no role holds a permission the matrix does not grant it.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from types import MappingProxyType
from typing import Final


class Role(StrEnum):
    """Roles a user can hold. Stored in ``user_roles``; everything else is code."""

    PASSENGER = "PASSENGER"
    DRIVER = "DRIVER"
    ADMIN = "ADMIN"
    # Platform owner: everything ADMIN can do plus roles, settings, flags, audit and PII.
    SUPER_ADMIN = "SUPER_ADMIN"


ADMIN_ROLES: Final[frozenset[Role]] = frozenset({Role.ADMIN, Role.SUPER_ADMIN})


class Permission(StrEnum):
    """``<domain>:<action>`` capabilities checked by ``require_permission``."""

    # Own account and profile (permission-matrix.md §2.1)
    ME_READ = "me:read"
    ME_UPDATE = "me:update"
    ME_DELETE = "me:delete"
    ME_SESSIONS_LIST = "me:sessions:list"
    ME_SESSIONS_REVOKE = "me:sessions:revoke"
    # S105 is suppressed below because the rule flags any name containing "password" as a
    # possible hardcoded secret; this is a permission identifier, not a credential.
    ME_PASSWORD_CHANGE = "me:password:change"  # noqa: S105

    # Other users (permission-matrix.md §2.1)
    USERS_READ_PUBLIC_PROFILE = "users:read_public_profile"

    # Verification (permission-matrix.md §2.2) — Phase 3
    VERIFICATION_IDENTITY_SUBMIT = "verification:identity:submit"
    VERIFICATION_IDENTITY_READ = "verification:identity:read"
    VERIFICATION_DRIVER_SUBMIT = "verification:driver:submit"
    VERIFICATION_DRIVER_READ = "verification:driver:read"
    VERIFICATION_DOCUMENT_DOWNLOAD = "verification:document:download"
    VERIFICATION_REVIEW = "verification:review"

    # Vehicles (permission-matrix.md §2.3) — Phase 3
    VEHICLES_CREATE = "vehicles:create"
    VEHICLES_READ = "vehicles:read"
    VEHICLES_UPDATE = "vehicles:update"
    VEHICLES_DOCUMENT_UPLOAD = "vehicles:document:upload"
    VEHICLES_REVIEW = "vehicles:review"

    # Trips (permission-matrix.md §2.4) — Phase 4
    TRIPS_CREATE = "trips:create"
    TRIPS_READ = "trips:read"
    TRIPS_UPDATE = "trips:update"
    TRIPS_PUBLISH = "trips:publish"
    TRIPS_START = "trips:start"
    TRIPS_COMPLETE = "trips:complete"
    TRIPS_CANCEL = "trips:cancel"
    TRIPS_LIST_OWN = "trips:list_own"
    MAPS_USE = "maps:use"
    PRICING_ESTIMATE = "pricing:estimate"
    SEARCH_TRIPS = "search:trips"

    # Join requests (permission-matrix.md §2.6) — Phase 6
    JOIN_REQUESTS_CREATE = "join_requests:create"
    JOIN_REQUESTS_READ = "join_requests:read"
    JOIN_REQUESTS_CANCEL = "join_requests:cancel"
    JOIN_REQUESTS_ACCEPT = "join_requests:accept"
    JOIN_REQUESTS_REJECT = "join_requests:reject"
    JOIN_REQUESTS_LIST_FOR_TRIP = "join_requests:list_for_trip"
    JOIN_REQUESTS_LIST_MINE = "join_requests:list_mine"

    # Chat & notifications (permission-matrix.md §2.7) — Phase 7
    CHAT_READ = "chat:read"
    CHAT_SEND = "chat:send"
    NOTIFICATIONS_READ = "notifications:read"
    NOTIFICATIONS_MANAGE = "notifications:manage"

    # Safety & trust (permission-matrix.md §2.8) — Phase 8
    RATINGS_CREATE = "ratings:create"
    RATINGS_READ = "ratings:read"
    REPORTS_CREATE = "reports:create"
    REPORTS_READ_OWN = "reports:read_own"
    BLOCKS_MANAGE = "blocks:manage"
    REPORTS_REVIEW = "reports:review"
    MODERATION_ACTION = "moderation:action"

    # Administration (permission-matrix.md §2.10) — Phase 9
    ADMIN_USERS_READ = "admin:users:read"
    ADMIN_USERS_MODERATE = "admin:users:moderate"
    ADMIN_USERS_DEACTIVATE = "admin:users:deactivate"
    ADMIN_ROLES_MANAGE = "admin:roles:manage"
    ADMIN_TRIPS_READ = "admin:trips:read"
    ADMIN_ANALYTICS_READ = "admin:analytics:read"
    ADMIN_SETTINGS_READ = "admin:settings:read"
    ADMIN_SETTINGS_WRITE = "admin:settings:write"
    ADMIN_FLAGS_MANAGE = "admin:feature_flags:manage"
    ADMIN_AUDIT_READ = "admin:audit:read"
    ADMIN_PII_READ = "admin:pii:read"

    # AI (permission-matrix.md §2.11) — Phase 10
    AI_ASSISTANT_QUERY = "ai:assistant:query"


# Everything a signed-in account can do regardless of role. `PASSENGER` is granted at
# registration (BR-ACC-01), so in practice every account holds these.
_SIGNED_IN: Final[frozenset[Permission]] = frozenset(
    {
        Permission.ME_READ,
        Permission.ME_UPDATE,
        Permission.ME_DELETE,
        Permission.ME_SESSIONS_LIST,
        Permission.ME_SESSIONS_REVOKE,
        Permission.ME_PASSWORD_CHANGE,
        Permission.USERS_READ_PUBLIC_PROFILE,
        Permission.VERIFICATION_IDENTITY_SUBMIT,
        Permission.VERIFICATION_IDENTITY_READ,
        Permission.VERIFICATION_DRIVER_SUBMIT,
        Permission.VERIFICATION_DRIVER_READ,
        Permission.VEHICLES_READ,
        Permission.VEHICLES_UPDATE,
        Permission.TRIPS_READ,
        Permission.TRIPS_LIST_OWN,
        Permission.MAPS_USE,
        Permission.PRICING_ESTIMATE,
        Permission.SEARCH_TRIPS,
        Permission.JOIN_REQUESTS_READ,
        Permission.CHAT_READ,
        Permission.CHAT_SEND,
        Permission.NOTIFICATIONS_READ,
        Permission.NOTIFICATIONS_MANAGE,
        Permission.RATINGS_CREATE,
        Permission.RATINGS_READ,
        Permission.REPORTS_CREATE,
        Permission.REPORTS_READ_OWN,
        Permission.BLOCKS_MANAGE,
        Permission.AI_ASSISTANT_QUERY,
    }
)

# Requesting and cancelling a seat is a passenger action. ADMIN does not receive it from the
# admin role; an administrator who also holds PASSENGER still can, via the union.
_JOIN_AS_PASSENGER: Final[frozenset[Permission]] = frozenset(
    {
        Permission.JOIN_REQUESTS_CREATE,
        Permission.JOIN_REQUESTS_CANCEL,
        Permission.JOIN_REQUESTS_LIST_MINE,
    }
)

_DRIVER_ONLY: Final[frozenset[Permission]] = frozenset(
    {
        Permission.TRIPS_CREATE,
        Permission.TRIPS_UPDATE,
        Permission.TRIPS_PUBLISH,
        Permission.TRIPS_START,
        Permission.TRIPS_COMPLETE,
        Permission.TRIPS_CANCEL,
        Permission.JOIN_REQUESTS_ACCEPT,
        Permission.JOIN_REQUESTS_REJECT,
        Permission.JOIN_REQUESTS_LIST_FOR_TRIP,
    }
)

# Applying to drive includes registering a vehicle (permission-matrix.md §2.3). ADMIN is
# excluded: administrators review vehicles, they do not create them through this API.
_APPLICANT: Final[frozenset[Permission]] = frozenset(
    {
        Permission.VEHICLES_CREATE,
        Permission.VEHICLES_DOCUMENT_UPLOAD,
    }
)

# Community moderators (the original WhatsApp-group admins).
_ADMIN_ONLY: Final[frozenset[Permission]] = frozenset(
    {
        Permission.VERIFICATION_DOCUMENT_DOWNLOAD,
        Permission.VERIFICATION_REVIEW,
        Permission.VEHICLES_REVIEW,
        Permission.JOIN_REQUESTS_LIST_FOR_TRIP,
        Permission.REPORTS_REVIEW,
        Permission.MODERATION_ACTION,
        Permission.ADMIN_USERS_READ,
        Permission.ADMIN_USERS_MODERATE,
        Permission.ADMIN_TRIPS_READ,
        Permission.ADMIN_ANALYTICS_READ,
    }
)

# Platform owner only (the developer). Never grantable through the HTTP API.
_SUPER_ADMIN_ONLY: Final[frozenset[Permission]] = frozenset(
    {
        Permission.ADMIN_USERS_DEACTIVATE,
        Permission.ADMIN_ROLES_MANAGE,
        Permission.ADMIN_SETTINGS_READ,
        Permission.ADMIN_SETTINGS_WRITE,
        Permission.ADMIN_FLAGS_MANAGE,
        Permission.ADMIN_AUDIT_READ,
        Permission.ADMIN_PII_READ,
    }
)

PERMISSIONS_BY_ROLE: Final[MappingProxyType[Role, frozenset[Permission]]] = MappingProxyType(
    {
        Role.PASSENGER: _SIGNED_IN | _APPLICANT | _JOIN_AS_PASSENGER,
        Role.DRIVER: _SIGNED_IN | _APPLICANT | _DRIVER_ONLY | _JOIN_AS_PASSENGER,
        Role.ADMIN: _SIGNED_IN | _ADMIN_ONLY,
        Role.SUPER_ADMIN: _SIGNED_IN | _ADMIN_ONLY | _SUPER_ADMIN_ONLY,
    }
)

ALL_PERMISSIONS: Final[frozenset[Permission]] = frozenset(Permission)


def permissions_for_roles(roles: Iterable[Role]) -> frozenset[Permission]:
    """Union of the permissions granted by ``roles`` (deny by default: no roles ⇒ nothing)."""
    granted: set[Permission] = set()
    for role in roles:
        granted |= PERMISSIONS_BY_ROLE.get(role, frozenset())
    return frozenset(granted)
