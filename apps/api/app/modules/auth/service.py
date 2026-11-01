"""Authentication flows (BR-AUTH-01 … BR-AUTH-09).

Every method takes the small :class:`RequestFacts` record instead of a FastAPI ``Request`` so the
rules can be tested without HTTP, and so it is obvious what request data the rules depend on.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz.permissions import Role
from app.core.authz.ports import SessionRevoker
from app.core.config import Settings
from app.core.email import EmailSender
from app.core.errors import (
    AppError,
    ConflictError,
    FieldError,
    NotFoundError,
    SessionRevokedError,
    UnauthenticatedError,
    ValidationAppError,
)
from app.core.ids import uuid7
from app.core.rate_limit import RateLimit, RateLimiter
from app.core.security import (
    PASSWORD_MAX_LENGTH,
    AccessTokenService,
    PasswordService,
    generate_opaque_token,
    hash_opaque_token,
    issue_csrf_token,
    keyed_hash,
    tokens_equal,
)
from app.core.sms import SmsDeliveryError, SmsMessage, SmsSender
from app.modules.audit.models import ActorType, AuditAction
from app.modules.audit.service import AuditLogWriter, IndependentAuditLogWriter
from app.modules.auth import emails
from app.modules.auth.models import AuthSession, SessionRevocationReason
from app.modules.auth.repository import SessionRepository, VerificationTokenRepository
from app.modules.users.models import AccountStatus
from app.modules.users.service import UserService

# Generic message for every failed sign-in: never says whether the address exists (BR-AUTH-03).
_SIGN_IN_FAILED = "Email address or password is incorrect."
_PHONE_CODE_ATTEMPTS = 5


class InvalidTokenError(AppError):
    """A verification or reset link that is unknown, already used or expired."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "INVALID_TOKEN"
    title = "Link is no longer valid"


@dataclass(frozen=True, slots=True)
class RequestFacts:
    """What the auth rules need to know about the HTTP request behind a call."""

    ip: str
    user_agent: str | None
    request_id: str | None


@dataclass(frozen=True, slots=True)
class IssuedSession:
    """A freshly issued credential pair plus the CSRF token bound to the session."""

    session_id: UUID
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime
    csrf_token: str


@dataclass(frozen=True, slots=True)
class SessionView:
    """One device/session as shown to its owner (BR-AUTH-08)."""

    id: UUID
    current: bool
    user_agent: str | None
    ip_fingerprint: str | None
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class RegistrationRequest:
    email: str
    password: str
    display_name: str
    full_name: str
    date_of_birth: date
    locale: str
    phone_e164: str | None
    accepted_terms_version: str
    accepted_privacy_version: str


class AuthService:
    """Owns credentials and sessions; delegates account data to the users module."""

    def __init__(
        self,
        *,
        users: UserService,
        sessions: SessionRepository,
        tokens: VerificationTokenRepository,
        passwords: PasswordService,
        access_tokens: AccessTokenService,
        email_sender: EmailSender,
        sms_sender: SmsSender,
        rate_limiter: RateLimiter,
        audit: AuditLogWriter,
        independent_audit: IndependentAuditLogWriter,
        settings: Settings,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._tokens = tokens
        self._passwords = passwords
        self._access_tokens = access_tokens
        self._emails = email_sender
        self._sms = sms_sender
        self._limiter = rate_limiter
        self._audit = audit
        self._independent_audit = independent_audit
        self._settings = settings

    # --- registration and email verification ---------------------------------------------

    async def register(self, request: RegistrationRequest, facts: RequestFacts) -> None:
        """Create an account and send the verification email (BR-ACC-01, BR-AUTH-04).

        Returns nothing in every case: the response must be identical whether the address was
        free or already taken (BR-AUTH-03).
        """
        await self._limiter.enforce(
            RateLimit.parse("auth_register_ip", self._settings.auth_register_rate_limit),
            self._hash(facts.ip),
        )
        self._check_password_policy(request.password, field="password")

        outcome = await self._users.register(
            email=request.email,
            password_hash=self._passwords.hash(request.password),
            display_name=request.display_name,
            full_name=request.full_name,
            date_of_birth=request.date_of_birth,
            locale=request.locale,
            phone_e164=request.phone_e164,
            accepted_terms_version=request.accepted_terms_version,
            accepted_privacy_version=request.accepted_privacy_version,
        )
        if not outcome.created:
            await self._emails.send(
                emails.existing_account_email(
                    to=outcome.email,
                    display_name=outcome.display_name,
                    locale=outcome.locale,
                    link=self._web_link(outcome.locale, "auth/sign-in"),
                )
            )
            return
        await self._send_verification_email(
            user_id=outcome.user_id,
            email=outcome.email,
            display_name=outcome.display_name,
            locale=outcome.locale,
        )

    async def resend_verification_email(self, email: str, facts: RequestFacts) -> None:
        """BR-AUTH-04. Answers identically for unknown and already-verified addresses."""
        await self._limiter.enforce(
            RateLimit.parse("auth_verify_resend", self._settings.auth_email_resend_rate_limit),
            self._hash(email.lower()),
        )
        credentials = await self._users.get_credentials(email)
        if (
            credentials is None
            or credentials.email_verified
            or credentials.status is not AccountStatus.ACTIVE
        ):
            return
        await self._send_verification_email(
            user_id=credentials.user_id,
            email=credentials.email,
            display_name=credentials.display_name,
            locale=credentials.locale,
        )

    async def verify_email(self, token: str) -> None:
        now = datetime.now(UTC)
        record = await self._tokens.consume_email_verification(hash_opaque_token(token), now)
        if record is None:
            raise InvalidTokenError("This confirmation link is no longer valid. Request a new one.")
        await self._users.mark_email_verified(record.user_id)

    async def start_phone_verification(
        self, user_id: UUID, phone_e164: str
    ) -> tuple[datetime, str | None]:
        """Send a code for this number. The code is returned only in local development."""
        now = datetime.now(UTC)
        subject = self._hash(f"phone:{user_id}")
        await self._limiter.enforce(RateLimit("phone_otp_start", 3, 600), subject)
        await self._users.assert_phone_available(user_id, phone_e164)
        code = f"{secrets.randbelow(1_000_000):06d}"
        expires_at = now + timedelta(minutes=self._settings.phone_otp_ttl_minutes)
        await self._tokens.issue_phone_code(
            user_id=user_id,
            phone_e164=phone_e164,
            code_hash=self._hash(f"{user_id}:{code}"),
            expires_at=expires_at,
            now=now,
        )
        account = await self._users.get_account(user_id)
        try:
            await self._sms.send(SmsMessage(to=phone_e164, body=_otp_text(account.locale, code)))
        except SmsDeliveryError as exc:
            raise AppError(
                "The confirmation code could not be sent. Try again in a moment.",
                code="SMS_FAILED",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc
        reveal = self._settings.app_env == "development" and not self._settings.sms_configured
        return expires_at, code if reveal else None

    async def confirm_phone(self, user_id: UUID, code: str) -> None:
        now = datetime.now(UTC)
        await self._limiter.enforce(
            RateLimit("phone_otp_confirm", 8, 600), self._hash(f"phone:{user_id}")
        )
        record = await self._tokens.active_phone_code(user_id, now)
        if record is None or record.attempts >= _PHONE_CODE_ATTEMPTS:
            raise InvalidTokenError("This confirmation code is not valid. Request a new one.")
        if not tokens_equal(record.code_hash, self._hash(f"{user_id}:{code}")):
            record.attempts += 1
            if record.attempts >= _PHONE_CODE_ATTEMPTS:
                record.used_at = now
            raise InvalidTokenError("This confirmation code is not valid. Request a new one.")
        try:
            await self._users.assign_verified_phone(user_id, record.phone_e164, now)
        except ConflictError:
            record.used_at = now
            raise
        record.used_at = now

    async def _send_verification_email(
        self, *, user_id: UUID, email: str, display_name: str, locale: str
    ) -> None:
        token = generate_opaque_token()
        now = datetime.now(UTC)
        await self._tokens.issue_email_verification(
            user_id=user_id,
            token_hash=hash_opaque_token(token),
            expires_at=now + timedelta(hours=self._settings.auth_email_verification_ttl_hours),
            now=now,
        )
        await self._emails.send(
            emails.verification_email(
                to=email,
                display_name=display_name,
                locale=locale,
                link=self._web_link(locale, "auth/verify-email", token=token),
            )
        )

    # --- sign in / refresh / sign out ----------------------------------------------------

    async def login(self, email: str, password: str, facts: RequestFacts) -> IssuedSession:
        """BR-AUTH-02, BR-AUTH-03."""
        identifier = self._hash(email.lower())
        await self._limiter.enforce(
            RateLimit.parse("auth_login_ip", self._settings.auth_login_rate_limit_per_ip),
            self._hash(facts.ip),
        )
        await self._limiter.enforce(
            RateLimit.parse(
                "auth_login_identifier", self._settings.auth_login_rate_limit_per_identifier
            ),
            identifier,
        )

        credentials = await self._users.get_credentials(email)
        if credentials is None:
            # Spend the same time as a real verification so the response cannot be used to
            # discover which addresses are registered.
            self._passwords.dummy_verify()
            await self._record_failed_login(facts, identifier=identifier, reason="UNKNOWN_EMAIL")
            raise UnauthenticatedError(_SIGN_IN_FAILED)

        if not self._passwords.verify(credentials.password_hash, password):
            await self._record_failed_login(
                facts, identifier=identifier, reason="BAD_PASSWORD", user_id=credentials.user_id
            )
            raise UnauthenticatedError(_SIGN_IN_FAILED)

        if credentials.status is AccountStatus.DELETED:
            # BR-ACC-07: signing in during the grace period cancels a pending deletion.
            restored = await self._users.restore_if_within_grace(credentials.user_id)
            if not restored:
                await self._record_failed_login(
                    facts,
                    identifier=identifier,
                    reason="ACCOUNT_DELETED",
                    user_id=credentials.user_id,
                )
                raise UnauthenticatedError(_SIGN_IN_FAILED)
        elif credentials.status is not AccountStatus.ACTIVE:
            await self._record_failed_login(
                facts,
                identifier=identifier,
                reason="ACCOUNT_NOT_ACTIVE",
                user_id=credentials.user_id,
            )
            raise UnauthenticatedError(_SIGN_IN_FAILED)

        if self._passwords.needs_rehash(credentials.password_hash):
            # Argon2 parameters were raised since this password was last used.
            await self._users.set_password_hash(credentials.user_id, self._passwords.hash(password))

        await self._users.record_login(credentials.user_id)
        issued = await self._start_session(credentials.user_id, facts)
        await self._audit.record(
            AuditAction.AUTH_LOGIN_SUCCESS,
            actor_type=ActorType.USER,
            actor_id=credentials.user_id,
            target_type="auth_session",
            target_id=issued.session_id,
            request_id=facts.request_id,
            ip_hash=self._hash(facts.ip),
        )
        return issued

    async def refresh(self, refresh_token: str, facts: RequestFacts) -> IssuedSession:
        """Rotate the refresh session, revoking the family if a used token comes back."""
        now = datetime.now(UTC)
        session = await self._sessions.get_by_token_hash(hash_opaque_token(refresh_token))
        if session is None:
            raise UnauthenticatedError("This session is no longer valid. Sign in again.")

        if session.is_revoked:
            await self._persist_refresh_reuse(session, facts)
            raise SessionRevokedError("This session was ended for security reasons. Sign in again.")

        if session.expires_at <= now or session.absolute_expires_at <= now:
            await self._sessions.revoke(session, SessionRevocationReason.LOGOUT, now)
            raise SessionRevokedError("This session has expired. Sign in again.")

        identity = await self._users.load_identity(session.user_id)
        if identity is None or not identity.is_active:
            await self._sessions.revoke_all_for_user(
                session.user_id, SessionRevocationReason.ACCOUNT_CLOSED, now
            )
            raise SessionRevokedError("This account can no longer sign in.")

        new_token = generate_opaque_token()
        rotated = await self._sessions.rotate(
            session,
            refresh_token_hash=hash_opaque_token(new_token),
            expires_at=min(now + self._refresh_ttl, session.absolute_expires_at),
            user_agent=facts.user_agent,
            ip_hash=self._hash(facts.ip),
            at=now,
        )
        await self._sessions.touch(rotated, now)
        return self._issue(rotated, new_token, identity.roles, now)

    async def logout(
        self, *, refresh_token: str | None, session_id: UUID | None, facts: RequestFacts
    ) -> None:
        """BR-AUTH-09: revoke the current session. Idempotent — never fails."""
        now = datetime.now(UTC)
        session: AuthSession | None = None
        if refresh_token is not None:
            session = await self._sessions.get_by_token_hash(hash_opaque_token(refresh_token))
        if session is None and session_id is not None:
            session = await self._sessions.get(session_id)
        if session is None or session.is_revoked:
            return
        await self._sessions.revoke(session, SessionRevocationReason.LOGOUT, now)
        await self._audit.record(
            AuditAction.AUTH_LOGOUT,
            actor_type=ActorType.USER,
            actor_id=session.user_id,
            target_type="auth_session",
            target_id=session.id,
            request_id=facts.request_id,
            ip_hash=self._hash(facts.ip),
        )

    # --- password reset and change -------------------------------------------------------

    async def forgot_password(self, email: str, facts: RequestFacts) -> None:
        """BR-AUTH-06. Always succeeds so the response reveals nothing (BR-AUTH-03)."""
        await self._limiter.enforce(
            RateLimit.parse("auth_forgot_ip", self._settings.auth_forgot_rate_limit_per_ip),
            self._hash(facts.ip),
        )
        await self._limiter.enforce(
            RateLimit.parse(
                "auth_forgot_identifier", self._settings.auth_forgot_rate_limit_per_identifier
            ),
            self._hash(email.lower()),
        )
        credentials = await self._users.get_credentials(email)
        if credentials is None or credentials.status is not AccountStatus.ACTIVE:
            return

        token = generate_opaque_token()
        now = datetime.now(UTC)
        await self._tokens.issue_password_reset(
            user_id=credentials.user_id,
            token_hash=hash_opaque_token(token),
            expires_at=now + timedelta(minutes=self._settings.auth_password_reset_ttl_minutes),
            now=now,
        )
        await self._emails.send(
            emails.password_reset_email(
                to=credentials.email,
                display_name=credentials.display_name,
                locale=credentials.locale,
                link=self._web_link(credentials.locale, "auth/reset-password", token=token),
            )
        )

    async def reset_password(self, token: str, new_password: str, facts: RequestFacts) -> None:
        """BR-AUTH-06: set the password and revoke every session of that user."""
        now = datetime.now(UTC)
        record = await self._tokens.consume_password_reset(hash_opaque_token(token), now)
        if record is None:
            raise InvalidTokenError("This reset link is no longer valid. Request a new one.")
        self._check_password_policy(new_password, field="newPassword")

        credentials = await self._users.get_credentials_by_id(record.user_id)
        if credentials is None or credentials.status is not AccountStatus.ACTIVE:
            raise InvalidTokenError("This reset link is no longer valid. Request a new one.")

        await self._users.set_password_hash(record.user_id, self._passwords.hash(new_password))
        revoked = await self._sessions.revoke_all_for_user(
            record.user_id, SessionRevocationReason.PASSWORD_RESET, now
        )
        await self._audit.record(
            AuditAction.AUTH_PASSWORD_RESET,
            actor_type=ActorType.USER,
            actor_id=record.user_id,
            target_type="user",
            target_id=record.user_id,
            request_id=facts.request_id,
            ip_hash=self._hash(facts.ip),
            metadata={"revoked_sessions": revoked},
        )
        await self._notify_password_changed(
            credentials.email, credentials.display_name, credentials.locale
        )

    async def change_password(
        self,
        *,
        user_id: UUID,
        current_session_id: UUID,
        current_password: str,
        new_password: str,
        facts: RequestFacts,
    ) -> int:
        """BR-AUTH-07: requires the current password; keeps only the calling session alive."""
        credentials = await self._users.get_credentials_by_id(user_id)
        if credentials is None:
            raise NotFoundError("Account not found.")
        if not self._passwords.verify(credentials.password_hash, current_password):
            raise ValidationAppError(
                "Current password is incorrect.",
                errors=[
                    FieldError(
                        field="currentPassword",
                        code="INVALID",
                        message="Current password is incorrect.",
                    )
                ],
            )
        self._check_password_policy(new_password, field="newPassword")

        now = datetime.now(UTC)
        await self._users.set_password_hash(user_id, self._passwords.hash(new_password))
        revoked = await self._sessions.revoke_all_for_user(
            user_id,
            SessionRevocationReason.PASSWORD_CHANGED,
            now,
            except_session_id=current_session_id,
        )
        await self._audit.record(
            AuditAction.AUTH_SESSION_REVOKED,
            actor_type=ActorType.USER,
            actor_id=user_id,
            target_type="user",
            target_id=user_id,
            request_id=facts.request_id,
            ip_hash=self._hash(facts.ip),
            metadata={
                "reason": SessionRevocationReason.PASSWORD_CHANGED.value,
                "revoked_sessions": revoked,
            },
        )
        await self._notify_password_changed(
            credentials.email, credentials.display_name, credentials.locale
        )
        return revoked

    async def _notify_password_changed(self, email: str, display_name: str, locale: str) -> None:
        await self._emails.send(
            emails.password_changed_email(
                to=email,
                display_name=display_name,
                locale=locale,
                link=self._web_link(locale, "auth/forgot-password"),
            )
        )

    # --- session management ---------------------------------------------------------------

    async def list_sessions(self, user_id: UUID, current_session_id: UUID) -> list[SessionView]:
        sessions = await self._sessions.list_for_user(user_id)
        return [
            SessionView(
                id=session.id,
                current=session.id == current_session_id,
                user_agent=session.user_agent,
                # A prefix of the keyed hash: enough to tell two devices apart, useless to
                # anyone who wants the address itself.
                ip_fingerprint=session.ip_hash[:12] if session.ip_hash else None,
                created_at=session.created_at,
                last_used_at=session.last_used_at,
                expires_at=session.expires_at,
            )
            for session in sessions
        ]

    async def revoke_session(self, *, user_id: UUID, session_id: UUID, facts: RequestFacts) -> None:
        session = await self._sessions.get(session_id)
        # 404 rather than 403: the caller must not learn that someone else's session exists.
        if session is None or session.user_id != user_id:
            raise NotFoundError("Session not found.")
        if session.is_revoked:
            return
        now = datetime.now(UTC)
        await self._sessions.revoke(session, SessionRevocationReason.USER_REVOKED, now)
        await self._audit.record(
            AuditAction.AUTH_SESSION_REVOKED,
            actor_type=ActorType.USER,
            actor_id=user_id,
            target_type="auth_session",
            target_id=session_id,
            request_id=facts.request_id,
            ip_hash=self._hash(facts.ip),
            metadata={"reason": SessionRevocationReason.USER_REVOKED.value},
        )

    # --- internals -----------------------------------------------------------------------

    @property
    def _refresh_ttl(self) -> timedelta:
        return timedelta(days=self._settings.auth_refresh_token_ttl_days)

    async def _start_session(self, user_id: UUID, facts: RequestFacts) -> IssuedSession:
        now = datetime.now(UTC)
        absolute = now + timedelta(days=self._settings.auth_refresh_absolute_ttl_days)
        token = generate_opaque_token()
        session = await self._sessions.create(
            user_id=user_id,
            refresh_token_hash=hash_opaque_token(token),
            family_id=uuid7(),
            user_agent=facts.user_agent,
            ip_hash=self._hash(facts.ip),
            expires_at=min(now + self._refresh_ttl, absolute),
            absolute_expires_at=absolute,
        )
        await self._sessions.touch(session, now)
        identity = await self._users.load_identity(user_id)
        roles = identity.roles if identity else frozenset()
        return self._issue(session, token, roles, now)

    def _issue(
        self,
        session: AuthSession,
        refresh_token: str,
        roles: frozenset[Role],
        now: datetime,
    ) -> IssuedSession:
        access_token = self._access_tokens.issue(
            user_id=session.user_id,
            session_id=session.id,
            roles=tuple(sorted(role.value for role in roles)),
            token_id=uuid7(),
            issued_at=now,
        )
        return IssuedSession(
            session_id=session.id,
            access_token=access_token,
            access_expires_at=now + self._access_tokens.ttl,
            refresh_token=refresh_token,
            refresh_expires_at=session.expires_at,
            csrf_token=issue_csrf_token(
                session.id, self._settings.auth_csrf_secret.get_secret_value()
            ),
        )

    def _check_password_policy(self, password: str, *, field: str) -> None:
        """BR-AUTH-01: length only — composition rules push users towards weaker passwords."""
        minimum = self._settings.auth_password_min_length
        if minimum <= len(password) <= PASSWORD_MAX_LENGTH:
            return
        message = f"Password must be between {minimum} and {PASSWORD_MAX_LENGTH} characters long."
        raise ValidationAppError(
            message,
            errors=[FieldError(field=field, code="LENGTH", message=message)],
        )

    async def _record_failed_login(
        self,
        facts: RequestFacts,
        *,
        identifier: str,
        reason: str,
        user_id: UUID | None = None,
    ) -> None:
        await self._independent_audit.record(
            AuditAction.AUTH_LOGIN_FAILED,
            actor_type=ActorType.USER,
            actor_id=user_id,
            target_type="user",
            target_id=user_id,
            request_id=facts.request_id,
            ip_hash=self._hash(facts.ip),
            metadata={"identifier_hash": identifier, "reason": reason},
        )

    async def _persist_refresh_reuse(self, session: AuthSession, facts: RequestFacts) -> None:
        """Revoke the family and audit it in a transaction that survives the 401 (ADR-0004)."""

        async def work(db: AsyncSession) -> None:
            revoked = await SessionRepository(db).revoke_family(
                session.family_id, SessionRevocationReason.REUSE_DETECTED, datetime.now(UTC)
            )
            await AuditLogWriter(db).record(
                AuditAction.AUTH_REFRESH_REUSE_DETECTED,
                actor_type=ActorType.USER,
                actor_id=session.user_id,
                target_type="auth_session",
                target_id=session.id,
                request_id=facts.request_id,
                ip_hash=self._hash(facts.ip),
                metadata={"revoked_sessions": revoked},
            )

        await self._independent_audit.in_own_transaction(work)

    def _hash(self, value: str) -> str:
        return keyed_hash(value, self._settings.auth_hash_secret.get_secret_value())

    def _web_link(self, locale: str, path: str, *, token: str | None = None) -> str:
        base = str(self._settings.public_web_url).rstrip("/")
        url = f"{base}/{locale}/{path}"
        return f"{url}?token={token}" if token else url


def make_session_revoker() -> SessionRevoker:
    """Build the :class:`~app.core.authz.ports.SessionRevoker` that ``app.main`` binds.

    Lets the users module end every session of an account it is closing (BR-ACC-07) without
    importing this module.
    """

    async def revoke(db: AsyncSession, user_id: UUID, reason: str) -> int:
        return await SessionRepository(db).revoke_all_for_user(
            user_id, SessionRevocationReason(reason), datetime.now(UTC)
        )

    return revoke


def _otp_text(locale: str, code: str) -> str:
    if locale == "en":
        return f"Fi Sikkati code: {code}. It expires in 10 minutes."
    return f"رمز في سكتي: {code}. بينتهي خلال 10 دقائق."
