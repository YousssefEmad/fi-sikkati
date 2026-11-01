"""FastAPI dependencies that authenticate the caller and enforce permissions.

Enforcement order (permission-matrix.md §3):

1. extract the credential (cookie for browsers, ``Authorization: Bearer`` otherwise);
2. verify the access-token signature and expiry;
3. for cookie-authenticated unsafe methods, verify ``Origin``/``Sec-Fetch-Site`` and the
   double-submit CSRF token;
4. load the current identity snapshot and reject non-``ACTIVE`` accounts;
5. check the required permission.

Deny by default: services take a :class:`Principal` rather than reading one from context, so a
route that forgets :func:`require_permission` cannot reach a protected service at all.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Annotated, Any
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz.permissions import Permission
from app.core.authz.ports import IdentityLoader, get_identity_loader
from app.core.authz.principal import Principal
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.errors import (
    AccountInactiveError,
    CsrfFailedError,
    ForbiddenError,
    TokenExpiredError,
    UnauthenticatedError,
)
from app.core.security import (
    ACCESS_COOKIE_NAME,
    CSRF_HEADER_NAME,
    AccessTokenService,
    ExpiredTokenError,
    TokenError,
    verify_csrf_token,
)

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
# ``same-origin``: first-party (the Next.js reverse-proxy in every environment, ADR-0004).
# ``same-site``: local two-port setup (web :3000 → API :8000 on localhost) before the proxy.
# ``none``: a user-initiated navigation. ``cross-site`` is always rejected.
_ALLOWED_FETCH_SITES = frozenset({"same-origin", "same-site", "none"})
_BEARER_PREFIX = "Bearer "


@dataclass(frozen=True, slots=True)
class Credential:
    """A raw access token plus how it arrived, which decides whether CSRF applies."""

    token: str
    from_cookie: bool


def get_access_token_service(request: Request) -> AccessTokenService:
    """Return the process-wide token service built during application startup."""
    service = getattr(request.app.state, "access_token_service", None)
    if not isinstance(service, AccessTokenService):  # pragma: no cover — wiring error
        msg = "AccessTokenService is not initialised on app.state"
        raise TypeError(msg)
    return service


def extract_credential(request: Request) -> Credential | None:
    """Prefer an explicit ``Authorization`` header; fall back to the browser cookie."""
    header = request.headers.get("authorization")
    if header and header.startswith(_BEARER_PREFIX):
        token = header[len(_BEARER_PREFIX) :].strip()
        if token:
            return Credential(token=token, from_cookie=False)
    cookie = request.cookies.get(ACCESS_COOKIE_NAME)
    if cookie:
        return Credential(token=cookie, from_cookie=True)
    return None


def _normalise_origin(value: str) -> str:
    parts = urlsplit(value)
    return f"{parts.scheme}://{parts.netloc}".lower().rstrip("/")


def allowed_origins(request: Request, settings: Settings) -> frozenset[str]:
    """Origins allowed to make cookie-authenticated mutations.

    The configured web origins plus the API's own origin: the web app calls the API through a
    same-origin reverse-proxy path in every environment (ADR-0004).
    """
    origins = {_normalise_origin(origin) for origin in settings.cors_origin_strings}
    origins.add(_normalise_origin(str(settings.public_web_url)))
    origins.add(_normalise_origin(str(request.base_url)))
    return frozenset(origins)


def enforce_same_site(request: Request, settings: Settings) -> None:
    """Reject cross-site mutations using ``Sec-Fetch-Site`` and ``Origin``.

    Used on its own by ``POST /auth/refresh``, where the session id is not known until the
    refresh token has been looked up, and as the first half of :func:`enforce_csrf` elsewhere.
    """
    if request.method in SAFE_METHODS:
        return
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site is not None and fetch_site not in _ALLOWED_FETCH_SITES:
        raise CsrfFailedError("Cross-site requests are not allowed for cookie sessions.")
    origin = request.headers.get("origin")
    if origin is not None and _normalise_origin(origin) not in allowed_origins(request, settings):
        raise CsrfFailedError("Request origin is not allowed.")


def enforce_csrf(
    request: Request, credential: Credential, session_id: UUID, settings: Settings
) -> None:
    """Reject cross-site cookie-authenticated mutations (security.md §1).

    Three independent checks: ``Sec-Fetch-Site`` (browsers only), ``Origin`` against the
    allow-list, and a double-submit token bound to the session id. Bearer clients are exempt
    because a cross-site page cannot set an ``Authorization`` header.
    """
    if not credential.from_cookie or request.method in SAFE_METHODS:
        return

    enforce_same_site(request, settings)
    token = request.headers.get(CSRF_HEADER_NAME)
    if not verify_csrf_token(token, session_id, settings.auth_csrf_secret.get_secret_value()):
        raise CsrfFailedError(f"A valid {CSRF_HEADER_NAME} header is required.")


async def get_optional_principal(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    tokens: Annotated[AccessTokenService, Depends(get_access_token_service)],
) -> Principal | None:
    """Resolve the caller when credentials are present; ``None`` for anonymous requests.

    A malformed or expired credential is still an error: silently treating it as anonymous would
    turn an authorization failure into a confusing empty result.
    """
    credential = extract_credential(request)
    if credential is None:
        return None

    try:
        claims = tokens.verify(credential.token)
    except ExpiredTokenError as exc:
        raise TokenExpiredError("The access token has expired.") from exc
    except TokenError as exc:
        raise UnauthenticatedError("The access token is not valid.") from exc

    enforce_csrf(request, credential, claims.session_id, settings)

    loader: IdentityLoader = get_identity_loader(request)
    identity = await loader(db, claims.user_id)
    if identity is None:
        # The token is signed but the account no longer exists.
        raise UnauthenticatedError("The account for this token no longer exists.")
    if not identity.is_active:
        raise AccountInactiveError("This account cannot be used. Contact support for help.")

    return Principal(
        user_id=claims.user_id,
        session_id=claims.session_id,
        roles=identity.roles,
        email_verified=identity.email_verified,
        phone_verified=identity.phone_verified,
        cookie_authenticated=credential.from_cookie,
    )


async def get_current_principal(
    principal: Annotated[Principal | None, Depends(get_optional_principal)],
) -> Principal:
    """Require an authenticated caller."""
    if principal is None:
        raise UnauthenticatedError("Sign in to continue.")
    return principal


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]
OptionalPrincipal = Annotated[Principal | None, Depends(get_optional_principal)]

PermissionDependency = Callable[[Principal], Coroutine[Any, Any, Principal]]


def require_permission(permission: Permission) -> PermissionDependency:
    """Dependency factory: allow the request only if the caller holds ``permission``."""

    async def dependency(principal: CurrentPrincipal) -> Principal:
        if not principal.has_permission(permission):
            raise ForbiddenError("You do not have permission to perform this action.")
        return principal

    return dependency
