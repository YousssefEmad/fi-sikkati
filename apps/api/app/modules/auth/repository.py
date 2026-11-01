"""All SQL for the auth module."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CursorResult, Result, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import uuid7
from app.modules.auth.models import (
    USER_AGENT_MAX_LENGTH,
    AuthSession,
    EmailVerificationToken,
    PasswordResetToken,
    PhoneVerificationCode,
    SessionRevocationReason,
)


def _rows_affected(result: Result[Any]) -> int:
    """Row count of an UPDATE. ``Result`` is the static type; UPDATEs return ``CursorResult``."""
    if isinstance(result, CursorResult):
        return result.rowcount
    raise TypeError(type(result).__name__)  # pragma: no cover — DML always yields CursorResult


class SessionRepository:
    """``auth_sessions``: creation, rotation and revocation."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        *,
        user_id: UUID,
        refresh_token_hash: str,
        family_id: UUID | None,
        user_agent: str | None,
        ip_hash: str | None,
        expires_at: datetime,
        absolute_expires_at: datetime,
    ) -> AuthSession:
        session = AuthSession(
            id=uuid7(),
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            family_id=family_id or uuid7(),
            user_agent=user_agent[:USER_AGENT_MAX_LENGTH] if user_agent else None,
            ip_hash=ip_hash,
            expires_at=expires_at,
            absolute_expires_at=absolute_expires_at,
        )
        self._db.add(session)
        await self._db.flush()
        return session

    async def get(self, session_id: UUID) -> AuthSession | None:
        return await self._db.get(AuthSession, session_id)

    async def get_by_token_hash(self, token_hash: str) -> AuthSession | None:
        result = await self._db.execute(
            select(AuthSession).where(AuthSession.refresh_token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: UUID) -> list[AuthSession]:
        result = await self._db.execute(
            select(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .order_by(AuthSession.created_at.desc())
        )
        return list(result.scalars())

    async def revoke(
        self, session: AuthSession, reason: SessionRevocationReason, at: datetime
    ) -> None:
        if session.revoked_at is None:
            session.revoked_at = at
            session.revoked_reason = reason
            await self._db.flush()

    async def revoke_family(
        self, family_id: UUID, reason: SessionRevocationReason, at: datetime
    ) -> int:
        """Revoke every live session in a rotation family (theft response, ADR-0004)."""
        result = await self._db.execute(
            update(AuthSession)
            .where(AuthSession.family_id == family_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=at, revoked_reason=reason)
        )
        await self._db.flush()
        return _rows_affected(result)

    async def revoke_all_for_user(
        self,
        user_id: UUID,
        reason: SessionRevocationReason,
        at: datetime,
        *,
        except_session_id: UUID | None = None,
    ) -> int:
        statement = update(AuthSession).where(
            AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)
        )
        if except_session_id is not None:
            statement = statement.where(AuthSession.id != except_session_id)
        result = await self._db.execute(statement.values(revoked_at=at, revoked_reason=reason))
        await self._db.flush()
        return _rows_affected(result)

    async def rotate(
        self,
        session: AuthSession,
        *,
        refresh_token_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_hash: str | None,
        at: datetime,
    ) -> AuthSession:
        """Replace the old session row with a new one in the same family.

        A new row (rather than an in-place token swap) keeps the device list honest and leaves
        the rotated row behind as the tripwire that detects a replayed token.
        """
        await self.revoke(session, SessionRevocationReason.ROTATED, at)
        return await self.create(
            user_id=session.user_id,
            refresh_token_hash=refresh_token_hash,
            family_id=session.family_id,
            user_agent=user_agent or session.user_agent,
            ip_hash=ip_hash or session.ip_hash,
            expires_at=expires_at,
            absolute_expires_at=session.absolute_expires_at,
        )

    async def touch(self, session: AuthSession, at: datetime) -> None:
        session.last_used_at = at
        await self._db.flush()


class VerificationTokenRepository:
    """``email_verification_tokens`` and ``password_reset_tokens``.

    Both tables behave identically: issue one, invalidate the user's previous ones, consume once.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def issue_email_verification(
        self, *, user_id: UUID, token_hash: str, expires_at: datetime, now: datetime
    ) -> EmailVerificationToken:
        await self._invalidate_email_verification(user_id, now)
        token = EmailVerificationToken(
            id=uuid7(), user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self._db.add(token)
        await self._db.flush()
        return token

    async def _invalidate_email_verification(self, user_id: UUID, now: datetime) -> None:
        await self._db.execute(
            update(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.used_at.is_(None),
            )
            .values(used_at=now)
        )

    async def consume_email_verification(
        self, token_hash: str, now: datetime
    ) -> EmailVerificationToken | None:
        """Return the token only if it exists, is unused and is not expired; mark it used."""
        result = await self._db.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash,
                EmailVerificationToken.used_at.is_(None),
                EmailVerificationToken.expires_at > now,
            )
        )
        token = result.scalar_one_or_none()
        if token is None:
            return None
        token.used_at = now
        await self._db.flush()
        return token

    async def issue_password_reset(
        self, *, user_id: UUID, token_hash: str, expires_at: datetime, now: datetime
    ) -> PasswordResetToken:
        await self._db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None))
            .values(used_at=now)
        )
        token = PasswordResetToken(
            id=uuid7(), user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self._db.add(token)
        await self._db.flush()
        return token

    async def consume_password_reset(
        self, token_hash: str, now: datetime
    ) -> PasswordResetToken | None:
        result = await self._db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
            )
        )
        token = result.scalar_one_or_none()
        if token is None:
            return None
        token.used_at = now
        await self._db.flush()
        return token

    async def issue_phone_code(
        self,
        *,
        user_id: UUID,
        phone_e164: str,
        code_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> PhoneVerificationCode:
        await self._db.execute(
            update(PhoneVerificationCode)
            .where(
                PhoneVerificationCode.user_id == user_id,
                PhoneVerificationCode.used_at.is_(None),
            )
            .values(used_at=now)
        )
        code = PhoneVerificationCode(
            id=uuid7(),
            user_id=user_id,
            phone_e164=phone_e164,
            code_hash=code_hash,
            expires_at=expires_at,
        )
        self._db.add(code)
        await self._db.flush()
        return code

    async def active_phone_code(self, user_id: UUID, now: datetime) -> PhoneVerificationCode | None:
        result = await self._db.execute(
            select(PhoneVerificationCode)
            .where(
                PhoneVerificationCode.user_id == user_id,
                PhoneVerificationCode.used_at.is_(None),
                PhoneVerificationCode.expires_at > now,
            )
            .order_by(PhoneVerificationCode.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
