"""``/auth`` and ``/me/sessions`` endpoints (api.md §4.2).

Routers do HTTP only: read the request, call the service, set cookies, serialise. Every rule is
in :mod:`app.modules.auth.service`.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.authz.dependencies import (
    CurrentPrincipal,
    enforce_same_site,
    require_permission,
)
from app.core.authz.permissions import Permission
from app.core.authz.principal import Principal
from app.core.config import Settings, get_settings
from app.core.cookies import clear_session_cookies, set_session_cookies
from app.core.errors import UnauthenticatedError
from app.core.security import REFRESH_COOKIE_NAME
from app.modules.auth.dependencies import AuthServiceDep, RequestFactsDep, TokensInBodyDep
from app.modules.auth.schemas import (
    AcceptedResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    PhoneConfirmRequest,
    PhoneStartRequest,
    PhoneStartResponse,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SessionListResponse,
    SessionResponse,
    SessionSummary,
    VerifyEmailRequest,
)
from app.modules.auth.service import IssuedSession, RegistrationRequest

router = APIRouter(prefix="/auth", tags=["auth"])
sessions_router = APIRouter(prefix="/me/sessions", tags=["auth"])


def _session_response(
    response: Response, issued: IssuedSession, *, include_tokens: bool
) -> SessionResponse:
    set_session_cookies(
        response,
        access_token=issued.access_token,
        access_expires_at=issued.access_expires_at,
        refresh_token=issued.refresh_token,
        refresh_expires_at=issued.refresh_expires_at,
        csrf_token=issued.csrf_token,
    )
    return SessionResponse(
        session_id=issued.session_id,
        access_token_expires_at=issued.access_expires_at,
        csrf_token=issued.csrf_token,
        access_token=issued.access_token if include_tokens else None,
        refresh_token=issued.refresh_token if include_tokens else None,
    )


@router.post(
    "/register",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AcceptedResponse,
    operation_id="auth_register",
    summary="Create an account",
    description=(
        "Always answers `202 ACCEPTED`, whether or not the address was already registered "
        "(BR-AUTH-03). The next step is the link in the email that follows."
    ),
)
async def register(
    payload: RegisterRequest, service: AuthServiceDep, facts: RequestFactsDep
) -> AcceptedResponse:
    await service.register(
        RegistrationRequest(
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
            full_name=payload.full_name,
            date_of_birth=payload.date_of_birth,
            locale=payload.locale,
            phone_e164=payload.phone,
            accepted_terms_version=payload.accepted_terms_version,
            accepted_privacy_version=payload.accepted_privacy_version,
        ),
        facts,
    )
    return AcceptedResponse()


@router.post(
    "/login",
    response_model=SessionResponse,
    operation_id="auth_login",
    summary="Sign in",
)
async def login(
    payload: LoginRequest,
    response: Response,
    service: AuthServiceDep,
    facts: RequestFactsDep,
    include_tokens: TokensInBodyDep,
) -> SessionResponse:
    issued = await service.login(payload.email, payload.password, facts)
    return _session_response(response, issued, include_tokens=include_tokens)


@router.post(
    "/refresh",
    response_model=SessionResponse,
    operation_id="auth_refresh",
    summary="Rotate the session",
    description=(
        "Browsers send the refresh cookie; other clients send the token in the body. The old "
        "token stops working immediately and replaying it ends the whole session family."
    ),
)
async def refresh(
    request: Request,
    response: Response,
    service: AuthServiceDep,
    facts: RequestFactsDep,
    include_tokens: TokensInBodyDep,
    settings: Annotated[Settings, Depends(get_settings)],
    payload: RefreshRequest | None = None,
) -> SessionResponse:
    cookie_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if cookie_token is not None:
        # The session id is unknown until the token is looked up, so the double-submit check
        # cannot run here; SameSite=Lax plus these two header checks cover the same attack.
        enforce_same_site(request, settings)
    body_token = payload.refresh_token if payload else None
    # An explicit body token is what an API client meant to use; the cookie is the browser fallback.
    token = body_token or cookie_token
    if not token:
        raise UnauthenticatedError("No refresh token was provided.")
    issued = await service.refresh(token, facts)
    return _session_response(response, issued, include_tokens=include_tokens)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="auth_logout",
    summary="Sign out of the current session",
    description="Idempotent (BR-AUTH-09): signing out twice is not an error.",
)
async def logout(
    response: Response,
    principal: CurrentPrincipal,
    service: AuthServiceDep,
    facts: RequestFactsDep,
) -> Response:
    await service.logout(refresh_token=None, session_id=principal.session_id, facts=facts)
    clear_session_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post(
    "/email/verify",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="auth_verify_email",
    summary="Confirm an email address",
)
async def verify_email(payload: VerifyEmailRequest, service: AuthServiceDep) -> None:
    await service.verify_email(payload.token)


@router.post(
    "/email/resend",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AcceptedResponse,
    operation_id="auth_resend_verification",
    summary="Send a new confirmation email",
)
async def resend_verification(
    payload: ResendVerificationRequest, service: AuthServiceDep, facts: RequestFactsDep
) -> AcceptedResponse:
    await service.resend_verification_email(payload.email, facts)
    return AcceptedResponse()


@router.post(
    "/password/forgot",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AcceptedResponse,
    operation_id="auth_forgot_password",
    summary="Start a password reset",
)
async def forgot_password(
    payload: ForgotPasswordRequest, service: AuthServiceDep, facts: RequestFactsDep
) -> AcceptedResponse:
    await service.forgot_password(payload.email, facts)
    return AcceptedResponse()


@router.post(
    "/password/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="auth_reset_password",
    summary="Finish a password reset",
    description="Signs every device out of the account (BR-AUTH-06).",
)
async def reset_password(
    payload: ResetPasswordRequest,
    response: Response,
    service: AuthServiceDep,
    facts: RequestFactsDep,
) -> Response:
    await service.reset_password(payload.token, payload.new_password, facts)
    # The caller's own cookies, if any, now point at a revoked session.
    clear_session_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post(
    "/password/change",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="auth_change_password",
    summary="Change the password of the signed-in account",
    description="Keeps the current session and signs every other device out (BR-AUTH-07).",
)
async def change_password(
    payload: ChangePasswordRequest,
    service: AuthServiceDep,
    facts: RequestFactsDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ME_PASSWORD_CHANGE))],
) -> None:
    await service.change_password(
        user_id=principal.user_id,
        current_session_id=principal.session_id,
        current_password=payload.current_password,
        new_password=payload.new_password,
        facts=facts,
    )


@sessions_router.get(
    "",
    response_model=SessionListResponse,
    operation_id="auth_list_sessions",
    summary="List the devices signed in to this account",
)
async def list_sessions(
    service: AuthServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ME_SESSIONS_LIST))],
) -> SessionListResponse:
    views = await service.list_sessions(principal.user_id, principal.session_id)
    return SessionListResponse(
        items=[
            SessionSummary(
                id=view.id,
                current=view.current,
                device=view.user_agent,
                ip_fingerprint=view.ip_fingerprint,
                created_at=view.created_at,
                last_used_at=view.last_used_at,
                expires_at=view.expires_at,
            )
            for view in views
        ]
    )


@sessions_router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="auth_revoke_session",
    summary="Sign a device out",
)
async def revoke_session(
    session_id: UUID,
    service: AuthServiceDep,
    facts: RequestFactsDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ME_SESSIONS_REVOKE))],
) -> None:
    await service.revoke_session(user_id=principal.user_id, session_id=session_id, facts=facts)


phone_router = APIRouter(prefix="/me/phone", tags=["auth"])


@phone_router.post(
    "/challenges",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PhoneStartResponse,
    operation_id="phone_start",
    summary="Send a confirmation code to a mobile number",
)
async def start_phone(
    payload: PhoneStartRequest,
    service: AuthServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ME_UPDATE))],
) -> PhoneStartResponse:
    expires_at, dev_code = await service.start_phone_verification(principal.user_id, payload.phone)
    return PhoneStartResponse(expires_at=expires_at, dev_code=dev_code)


@phone_router.post(
    "/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="phone_confirm",
    summary="Confirm the mobile number with the SMS code",
)
async def confirm_phone(
    payload: PhoneConfirmRequest,
    service: AuthServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ME_UPDATE))],
) -> None:
    await service.confirm_phone(principal.user_id, payload.code)
