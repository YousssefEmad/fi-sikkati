"""The executable mirror of `permission-matrix.md` (testing.md §4, ADR-0005).

Three things are asserted here, all of which fail loudly when a route is added without thinking
about authorization:

* every route of ``/api/v1`` is classified below as public, authenticated or permission-guarded;
* every declared :class:`Permission` is reachable through at least one route;
* every guarded route rejects anonymous callers.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.core.authz.permissions import (
    ALL_PERMISSIONS,
    PERMISSIONS_BY_ROLE,
    Permission,
    Role,
    permissions_for_roles,
)
from tests.support.http import error_code

#: Routes anybody may call. Each entry is justified by `permission-matrix.md` §1: the four
#: credential-recovery endpoints must work precisely when the caller has no session.
PUBLIC_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/api/v1/platform/config"),
        ("POST", "/api/v1/auth/register"),
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/refresh"),
        ("POST", "/api/v1/auth/email/verify"),
        ("POST", "/api/v1/auth/email/resend"),
        ("POST", "/api/v1/auth/password/forgot"),
        ("POST", "/api/v1/auth/password/reset"),
    }
)

#: Routes that need a session but no particular capability: signing out is something every
#: authenticated caller may always do (BR-AUTH-09).
AUTHENTICATED_ROUTES: frozenset[tuple[str, str]] = frozenset({("POST", "/api/v1/auth/logout")})

#: ``(method, path, permission)`` for every guarded route.
GUARDED_ROUTES: tuple[tuple[str, str, Permission], ...] = (
    ("GET", "/api/v1/me", Permission.ME_READ),
    ("PATCH", "/api/v1/me", Permission.ME_UPDATE),
    ("POST", "/api/v1/me/phone/challenges", Permission.ME_UPDATE),
    ("POST", "/api/v1/me/phone/confirm", Permission.ME_UPDATE),
    ("POST", "/api/v1/me/photo", Permission.ME_UPDATE),
    ("DELETE", "/api/v1/me", Permission.ME_DELETE),
    ("POST", "/api/v1/auth/password/change", Permission.ME_PASSWORD_CHANGE),
    ("GET", "/api/v1/me/sessions", Permission.ME_SESSIONS_LIST),
    ("DELETE", "/api/v1/me/sessions/{session_id}", Permission.ME_SESSIONS_REVOKE),
    (
        "GET",
        "/api/v1/users/{user_id}/public-profile",
        Permission.USERS_READ_PUBLIC_PROFILE,
    ),
    ("GET", "/api/v1/me/verification", Permission.VERIFICATION_IDENTITY_READ),
    ("GET", "/api/v1/me/verification", Permission.VERIFICATION_DRIVER_READ),
    (
        "POST",
        "/api/v1/me/verification/identity/documents",
        Permission.VERIFICATION_IDENTITY_SUBMIT,
    ),
    ("POST", "/api/v1/me/verification/identity/submit", Permission.VERIFICATION_IDENTITY_SUBMIT),
    ("POST", "/api/v1/me/verification/driver/documents", Permission.VERIFICATION_DRIVER_SUBMIT),
    ("POST", "/api/v1/me/verification/driver/submit", Permission.VERIFICATION_DRIVER_SUBMIT),
    ("GET", "/api/v1/me/vehicles", Permission.VEHICLES_READ),
    ("POST", "/api/v1/me/vehicles", Permission.VEHICLES_CREATE),
    ("GET", "/api/v1/me/vehicles/{vehicle_id}", Permission.VEHICLES_READ),
    ("PATCH", "/api/v1/me/vehicles/{vehicle_id}", Permission.VEHICLES_UPDATE),
    ("POST", "/api/v1/me/vehicles/{vehicle_id}/deactivate", Permission.VEHICLES_UPDATE),
    (
        "POST",
        "/api/v1/me/vehicles/{vehicle_id}/documents",
        Permission.VEHICLES_DOCUMENT_UPLOAD,
    ),
    ("GET", "/api/v1/admin/verifications/identity", Permission.VERIFICATION_REVIEW),
    ("GET", "/api/v1/admin/verifications/identity/{user_id}", Permission.VERIFICATION_REVIEW),
    (
        "POST",
        "/api/v1/admin/verifications/identity/{user_id}/approve",
        Permission.VERIFICATION_REVIEW,
    ),
    (
        "POST",
        "/api/v1/admin/verifications/identity/{user_id}/reject",
        Permission.VERIFICATION_REVIEW,
    ),
    ("GET", "/api/v1/admin/verifications/driver", Permission.VERIFICATION_REVIEW),
    ("GET", "/api/v1/admin/verifications/driver/{user_id}", Permission.VERIFICATION_REVIEW),
    (
        "POST",
        "/api/v1/admin/verifications/driver/{user_id}/approve",
        Permission.VERIFICATION_REVIEW,
    ),
    (
        "POST",
        "/api/v1/admin/verifications/driver/{user_id}/registration",
        Permission.VERIFICATION_REVIEW,
    ),
    ("POST", "/api/v1/admin/verifications/driver/{user_id}/reject", Permission.VERIFICATION_REVIEW),
    (
        "GET",
        "/api/v1/admin/verifications/files/{file_id}/download-url",
        Permission.VERIFICATION_DOCUMENT_DOWNLOAD,
    ),
    ("GET", "/api/v1/admin/vehicles", Permission.VEHICLES_REVIEW),
    ("GET", "/api/v1/admin/vehicles/{vehicle_id}", Permission.VEHICLES_REVIEW),
    ("POST", "/api/v1/admin/vehicles/{vehicle_id}/approve", Permission.VEHICLES_REVIEW),
    ("POST", "/api/v1/admin/vehicles/{vehicle_id}/reject", Permission.VEHICLES_REVIEW),
    ("POST", "/api/v1/admin/vehicles/{vehicle_id}/deactivate", Permission.VEHICLES_UPDATE),
    ("GET", "/api/v1/maps/autocomplete", Permission.MAPS_USE),
    ("GET", "/api/v1/maps/geocode", Permission.MAPS_USE),
    ("POST", "/api/v1/maps/route-preview", Permission.MAPS_USE),
    ("GET", "/api/v1/pricing/estimate", Permission.PRICING_ESTIMATE),
    ("POST", "/api/v1/trips", Permission.TRIPS_CREATE),
    ("GET", "/api/v1/trips/{trip_id}", Permission.TRIPS_READ),
    ("PATCH", "/api/v1/trips/{trip_id}", Permission.TRIPS_UPDATE),
    ("POST", "/api/v1/trips/{trip_id}/publish", Permission.TRIPS_PUBLISH),
    ("POST", "/api/v1/trips/{trip_id}/start", Permission.TRIPS_START),
    ("POST", "/api/v1/trips/{trip_id}/complete", Permission.TRIPS_COMPLETE),
    ("POST", "/api/v1/trips/{trip_id}/cancel", Permission.TRIPS_CANCEL),
    ("GET", "/api/v1/me/trips", Permission.TRIPS_LIST_OWN),
    ("GET", "/api/v1/search/trips", Permission.SEARCH_TRIPS),
    ("POST", "/api/v1/trips/{trip_id}/join-requests", Permission.JOIN_REQUESTS_CREATE),
    ("GET", "/api/v1/trips/{trip_id}/call-contacts", Permission.TRIPS_READ),
    ("GET", "/api/v1/trips/{trip_id}/join-requests", Permission.JOIN_REQUESTS_LIST_FOR_TRIP),
    ("GET", "/api/v1/me/join-requests", Permission.JOIN_REQUESTS_LIST_MINE),
    ("GET", "/api/v1/join-requests/{request_id}", Permission.JOIN_REQUESTS_READ),
    ("POST", "/api/v1/join-requests/{request_id}/accept", Permission.JOIN_REQUESTS_ACCEPT),
    ("POST", "/api/v1/join-requests/{request_id}/reject", Permission.JOIN_REQUESTS_REJECT),
    ("POST", "/api/v1/join-requests/{request_id}/cancel", Permission.JOIN_REQUESTS_CANCEL),
    ("GET", "/api/v1/me/conversations", Permission.CHAT_READ),
    ("GET", "/api/v1/conversations/{conversation_id}", Permission.CHAT_READ),
    ("GET", "/api/v1/conversations/{conversation_id}/messages", Permission.CHAT_READ),
    ("POST", "/api/v1/conversations/{conversation_id}/messages", Permission.CHAT_SEND),
    ("POST", "/api/v1/conversations/{conversation_id}/read", Permission.CHAT_READ),
    ("GET", "/api/v1/me/notifications", Permission.NOTIFICATIONS_READ),
    ("GET", "/api/v1/me/notifications/unread-count", Permission.NOTIFICATIONS_READ),
    ("POST", "/api/v1/me/notifications/read", Permission.NOTIFICATIONS_MANAGE),
    ("GET", "/api/v1/me/notification-preferences", Permission.NOTIFICATIONS_READ),
    ("PUT", "/api/v1/me/notification-preferences", Permission.NOTIFICATIONS_MANAGE),
    ("PUT", "/api/v1/me/push-subscriptions", Permission.NOTIFICATIONS_MANAGE),
    ("DELETE", "/api/v1/me/push-subscriptions", Permission.NOTIFICATIONS_MANAGE),
    ("POST", "/api/v1/trips/{trip_id}/ratings", Permission.RATINGS_CREATE),
    ("GET", "/api/v1/users/{user_id}/ratings/summary", Permission.RATINGS_READ),
    ("POST", "/api/v1/reports", Permission.REPORTS_CREATE),
    ("GET", "/api/v1/me/reports", Permission.REPORTS_READ_OWN),
    ("GET", "/api/v1/me/blocks", Permission.BLOCKS_MANAGE),
    ("POST", "/api/v1/me/blocks", Permission.BLOCKS_MANAGE),
    ("DELETE", "/api/v1/me/blocks/{user_id}", Permission.BLOCKS_MANAGE),
    ("GET", "/api/v1/admin/users", Permission.ADMIN_USERS_READ),
    ("GET", "/api/v1/admin/users/{user_id}", Permission.ADMIN_USERS_READ),
    ("GET", "/api/v1/admin/users/{user_id}/contact", Permission.ADMIN_PII_READ),
    ("POST", "/api/v1/admin/users/{user_id}/suspend", Permission.ADMIN_USERS_MODERATE),
    ("POST", "/api/v1/admin/users/{user_id}/restore", Permission.ADMIN_USERS_MODERATE),
    ("POST", "/api/v1/admin/users/{user_id}/deactivate", Permission.ADMIN_USERS_DEACTIVATE),
    ("PUT", "/api/v1/admin/users/{user_id}/roles", Permission.ADMIN_ROLES_MANAGE),
    ("GET", "/api/v1/admin/trips", Permission.ADMIN_TRIPS_READ),
    ("GET", "/api/v1/admin/reports", Permission.REPORTS_REVIEW),
    ("GET", "/api/v1/admin/reports/{report_id}", Permission.REPORTS_REVIEW),
    ("POST", "/api/v1/admin/reports/{report_id}/status", Permission.REPORTS_REVIEW),
    ("POST", "/api/v1/admin/reports/{report_id}/actions", Permission.MODERATION_ACTION),
    ("GET", "/api/v1/admin/analytics/overview", Permission.ADMIN_ANALYTICS_READ),
    ("GET", "/api/v1/admin/analytics/timeseries", Permission.ADMIN_ANALYTICS_READ),
    ("GET", "/api/v1/admin/settings", Permission.ADMIN_SETTINGS_READ),
    ("PUT", "/api/v1/admin/settings/{key}", Permission.ADMIN_SETTINGS_WRITE),
    ("GET", "/api/v1/admin/feature-flags", Permission.ADMIN_FLAGS_MANAGE),
    ("PUT", "/api/v1/admin/feature-flags/{key}", Permission.ADMIN_FLAGS_MANAGE),
    ("GET", "/api/v1/admin/audit-logs", Permission.ADMIN_AUDIT_READ),
    ("POST", "/api/v1/ai/assistant", Permission.AI_ASSISTANT_QUERY),
)

_PLACEHOLDER_ID = UUID("01924000-0000-7000-8000-000000000000")


def _api_routes(app: FastAPI) -> set[tuple[str, str]]:
    """Paths from the generated OpenAPI document.

    That is the same source the generated client and this matrix share.
    """
    found: set[tuple[str, str]] = set()
    for path, operations in app.openapi()["paths"].items():
        if path.endswith("/openapi.json"):
            continue
        found |= {
            (method.upper(), path)
            for method, spec in operations.items()
            if method in {"get", "post", "put", "patch", "delete"} and isinstance(spec, dict)
        }
    return found


def _concrete(path: str) -> str:
    for name in (
        "session_id",
        "user_id",
        "vehicle_id",
        "file_id",
        "trip_id",
        "request_id",
        "conversation_id",
        "report_id",
        "key",
        "id",
    ):
        path = path.replace(f"{{{name}}}", str(_PLACEHOLDER_ID))
    return path


def test_every_route_is_classified(app: FastAPI) -> None:
    """A new route must be added to one of the three tables above, consciously."""
    classified = (
        PUBLIC_ROUTES
        | AUTHENTICATED_ROUTES
        | {(method, path) for method, path, _ in GUARDED_ROUTES}
    )
    assert _api_routes(app) == classified


def test_every_permission_guards_a_route() -> None:
    """No permission may exist without an endpoint that enforces it (ADR-0005)."""
    assert {permission for _, _, permission in GUARDED_ROUTES} == set(ALL_PERMISSIONS)


def test_passenger_and_driver_can_apply_and_cannot_review() -> None:
    for role in (Role.PASSENGER, Role.DRIVER):
        granted = PERMISSIONS_BY_ROLE[role]
        assert Permission.VEHICLES_CREATE in granted
        assert Permission.VERIFICATION_IDENTITY_SUBMIT in granted
        assert Permission.VERIFICATION_REVIEW not in granted
        assert Permission.VERIFICATION_DOCUMENT_DOWNLOAD not in granted
        assert Permission.VEHICLES_REVIEW not in granted


def test_admin_reviews_but_does_not_register_vehicles() -> None:
    granted = PERMISSIONS_BY_ROLE[Role.ADMIN]
    assert Permission.VERIFICATION_REVIEW in granted
    assert Permission.VERIFICATION_DOCUMENT_DOWNLOAD in granted
    assert Permission.VEHICLES_REVIEW in granted
    assert Permission.VEHICLES_CREATE not in granted
    assert Permission.VEHICLES_DOCUMENT_UPLOAD not in granted


def test_no_roles_grants_nothing() -> None:
    """Deny by default: an account with no role can do nothing at all."""
    assert permissions_for_roles([]) == frozenset()


@pytest.mark.parametrize(
    ("method", "path"),
    [(method, path) for method, path, _ in GUARDED_ROUTES] + sorted(AUTHENTICATED_ROUTES),
)
async def test_anonymous_callers_are_rejected(client: AsyncClient, method: str, path: str) -> None:
    response = await client.request(method, _concrete(path), json={})
    assert response.status_code == 401
    assert error_code(response) == "UNAUTHENTICATED"


@pytest.mark.parametrize(
    ("method", "path"),
    [(method, path) for method, path, _ in GUARDED_ROUTES],
)
async def test_invalid_token_is_rejected(client: AsyncClient, method: str, path: str) -> None:
    response = await client.request(
        method,
        _concrete(path),
        json={},
        headers={"Authorization": "Bearer not.a.token"},
    )
    assert response.status_code == 401
