"""``auth_sessions``, ``email_verification_tokens``, ``password_reset_tokens`` (database.md §2.1).

Only hashes of the opaque tokens are stored, so a database leak cannot be replayed against the
API (security.md §1).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Final
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, CreatedAtMixin, TimestampMixin, uuid_primary_key

USER_AGENT_MAX_LENGTH: Final = 300


class SessionRevocationReason(StrEnum):
    """Why a refresh session stopped being usable (database.md §2.1)."""

    LOGOUT = "LOGOUT"
    ROTATED = "ROTATED"
    REUSE_DETECTED = "REUSE_DETECTED"
    # S105 is suppressed below: these are enum member values, not credentials.
    PASSWORD_CHANGED = "PASSWORD_CHANGED"  # noqa: S105
    PASSWORD_RESET = "PASSWORD_RESET"  # noqa: S105
    USER_REVOKED = "USER_REVOKED"
    ACCOUNT_CLOSED = "ACCOUNT_CLOSED"


REVOCATION_REASON_ENUM: Final = Enum(
    SessionRevocationReason,
    name="auth_sessions_revoked_reason_enum",
    values_callable=lambda members: [member.value for member in members],
)


class AuthSession(Base, TimestampMixin):
    """One refresh session. Its id is the ``sid`` claim of the access tokens it issued."""

    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index(
            "ix_auth_sessions_user_id_active",
            "user_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
        Index("ix_auth_sessions_expires_at", "expires_at"),
        Index("ix_auth_sessions_family_id", "family_id"),
    )

    id: Mapped[UUID] = uuid_primary_key()
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # Rotation chain: reusing any token in a family revokes the whole family (ADR-0004).
    family_id: Mapped[UUID] = mapped_column(nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[SessionRevocationReason | None] = mapped_column(
        REVOCATION_REASON_ENUM, nullable=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None


class EmailVerificationToken(Base, CreatedAtMixin):
    """Single-use email verification token (BR-AUTH-04)."""

    __tablename__ = "email_verification_tokens"
    __table_args__ = (Index("ix_email_verification_tokens_user_id", "user_id"),)

    id: Mapped[UUID] = uuid_primary_key()
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PhoneVerificationCode(Base, CreatedAtMixin):
    """Single-use SMS code for the phone number a signed-in user is confirming."""

    __tablename__ = "phone_verification_codes"
    __table_args__ = (Index("ix_phone_verification_codes_user_id", "user_id"),)

    id: Mapped[UUID] = uuid_primary_key()
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    phone_e164: Mapped[str] = mapped_column(Text, nullable=False)
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    attempts: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PasswordResetToken(Base, CreatedAtMixin):
    """Single-use password reset token (BR-AUTH-06)."""

    __tablename__ = "password_reset_tokens"
    __table_args__ = (Index("ix_password_reset_tokens_user_id", "user_id"),)

    id: Mapped[UUID] = uuid_primary_key()
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
