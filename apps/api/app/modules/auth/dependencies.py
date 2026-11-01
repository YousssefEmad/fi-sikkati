"""FastAPI wiring for the auth module."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_database, get_db_session
from app.core.email import EmailSender
from app.core.rate_limit import RateLimiter, client_ip, get_rate_limiter
from app.core.request_id import get_request_id
from app.core.security import AccessTokenService, PasswordService
from app.core.sms import SmsSender
from app.modules.audit.service import AuditLogWriter, IndependentAuditLogWriter
from app.modules.auth.repository import SessionRepository, VerificationTokenRepository
from app.modules.auth.service import AuthService, RequestFacts
from app.modules.users.dependencies import UserServiceDep

#: Non-browser clients opt in to receiving tokens in the response body with this header; browsers
#: must not, because a token in a readable body defeats the HttpOnly cookie (api.md §1).
CLIENT_TYPE_HEADER = "X-Client-Type"
API_CLIENT_TYPE = "api"


def get_password_service(request: Request) -> PasswordService:
    service = getattr(request.app.state, "password_service", None)
    if not isinstance(service, PasswordService):  # pragma: no cover — wiring error
        msg = "PasswordService is not initialised on app.state"
        raise TypeError(msg)
    return service


def get_access_tokens(request: Request) -> AccessTokenService:
    service = getattr(request.app.state, "access_token_service", None)
    if not isinstance(service, AccessTokenService):  # pragma: no cover — wiring error
        msg = "AccessTokenService is not initialised on app.state"
        raise TypeError(msg)
    return service


def get_sms_sender(request: Request) -> SmsSender:
    sender = getattr(request.app.state, "sms_sender", None)
    if sender is None:  # pragma: no cover — wiring error
        msg = "SmsSender is not initialised on app.state"
        raise TypeError(msg)
    return sender  # type: ignore[no-any-return]


def get_email_sender(request: Request) -> EmailSender:
    sender = getattr(request.app.state, "email_sender", None)
    if sender is None:  # pragma: no cover — wiring error
        msg = "EmailSender is not initialised on app.state"
        raise TypeError(msg)
    return sender  # type: ignore[no-any-return]


def get_request_facts(request: Request) -> RequestFacts:
    """Collect the request data the auth rules need, hashing nothing yet."""
    return RequestFacts(
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent"),
        request_id=get_request_id(request),
    )


def wants_tokens_in_body(request: Request) -> bool:
    return request.headers.get(CLIENT_TYPE_HEADER, "").lower() == API_CLIENT_TYPE


def get_auth_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    users: UserServiceDep,
    settings: Annotated[Settings, Depends(get_settings)],
    passwords: Annotated[PasswordService, Depends(get_password_service)],
    access_tokens: Annotated[AccessTokenService, Depends(get_access_tokens)],
    email_sender: Annotated[EmailSender, Depends(get_email_sender)],
    sms_sender: Annotated[SmsSender, Depends(get_sms_sender)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> AuthService:
    return AuthService(
        users=users,
        sessions=SessionRepository(db),
        tokens=VerificationTokenRepository(db),
        passwords=passwords,
        access_tokens=access_tokens,
        email_sender=email_sender,
        sms_sender=sms_sender,
        rate_limiter=rate_limiter,
        audit=AuditLogWriter(db),
        independent_audit=IndependentAuditLogWriter(get_database(request).session_factory),
        settings=settings,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
RequestFactsDep = Annotated[RequestFacts, Depends(get_request_facts)]
TokensInBodyDep = Annotated[bool, Depends(wants_tokens_in_body)]
