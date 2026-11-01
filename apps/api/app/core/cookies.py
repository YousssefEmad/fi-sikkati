"""Cookie transport for browser clients (ADR-0004).

Three cookies, each with the narrowest scope that still works:

* ``__Host-fs_access`` — HttpOnly, sent to every API path.
* ``__Secure-fs_refresh`` — HttpOnly, path-scoped to the refresh endpoint, so a cross-site
  script bug elsewhere in the app cannot reach the long-lived credential. (It cannot use the
  ``__Host-`` prefix, which mandates ``Path=/``.)
* ``__Host-fs_csrf`` — readable by JavaScript on purpose: the client echoes it back in the
  ``X-CSRF-Token`` header for the double-submit check.

All three require HTTPS. ``http://localhost`` counts as a secure context in current browsers, so
local development works unchanged.

This lives in ``core`` because both the auth module (issuing) and the users module (closing an
account) need it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final, Literal

from fastapi import Response

from app.core.security import (
    ACCESS_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    REFRESH_COOKIE_PATH,
)

_SAME_SITE: Final[Literal["lax"]] = "lax"


def _max_age(expires_at: datetime) -> int:
    return max(int((expires_at - datetime.now(UTC)).total_seconds()), 0)


def set_session_cookies(
    response: Response,
    *,
    access_token: str,
    access_expires_at: datetime,
    refresh_token: str,
    refresh_expires_at: datetime,
    csrf_token: str,
) -> None:
    """Attach the access, refresh and CSRF cookies for a freshly issued session."""
    refresh_max_age = _max_age(refresh_expires_at)
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        access_token,
        max_age=_max_age(access_expires_at),
        path="/",
        httponly=True,
        secure=True,
        samesite=_SAME_SITE,
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=refresh_max_age,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=True,
        samesite=_SAME_SITE,
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        # The refresh lifetime, so the token outlives the access token and is still available
        # for the refresh call itself.
        max_age=refresh_max_age,
        path="/",
        httponly=False,
        secure=True,
        samesite=_SAME_SITE,
    )


def clear_session_cookies(response: Response) -> None:
    """Remove all three cookies. Paths must match the ones used when setting them."""
    for name, path in (
        (ACCESS_COOKIE_NAME, "/"),
        (REFRESH_COOKIE_NAME, REFRESH_COOKIE_PATH),
        (CSRF_COOKIE_NAME, "/"),
    ):
        response.delete_cookie(
            name, path=path, httponly=name != CSRF_COOKIE_NAME, secure=True, samesite=_SAME_SITE
        )
