"""``audit_logs`` (database.md §2.9)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Final
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, CreatedAtMixin, uuid_primary_key


class ActorType(StrEnum):
    """Who performed the audited action. ``SYSTEM`` is the background worker identity."""

    USER = "USER"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


class AuditAction(StrEnum):
    """The closed action vocabulary from security.md §9.

    Kept complete rather than per-phase so the vocabulary has exactly one definition; a test
    asserts it matches the documented list.
    """

    AUTH_LOGIN_SUCCESS = "AUTH_LOGIN_SUCCESS"
    AUTH_LOGIN_FAILED = "AUTH_LOGIN_FAILED"
    AUTH_LOGOUT = "AUTH_LOGOUT"
    AUTH_SESSION_REVOKED = "AUTH_SESSION_REVOKED"
    AUTH_REFRESH_REUSE_DETECTED = "AUTH_REFRESH_REUSE_DETECTED"
    AUTH_PASSWORD_RESET = "AUTH_PASSWORD_RESET"  # noqa: S105 — an action name, not a secret
    VERIFICATION_SUBMITTED = "VERIFICATION_SUBMITTED"
    VERIFICATION_APPROVED = "VERIFICATION_APPROVED"
    VERIFICATION_REJECTED = "VERIFICATION_REJECTED"
    DRIVER_REVOKED = "DRIVER_REVOKED"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_VIEWED = "DOCUMENT_VIEWED"
    DOCUMENT_PURGED = "DOCUMENT_PURGED"
    ROLE_GRANTED = "ROLE_GRANTED"
    ROLE_REVOKED = "ROLE_REVOKED"
    USER_SUSPENDED = "USER_SUSPENDED"
    USER_RESTORED = "USER_RESTORED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    USER_ANONYMISED = "USER_ANONYMISED"
    TRIP_CANCELLED_BY_ADMIN = "TRIP_CANCELLED_BY_ADMIN"
    TRIP_EXPIRED = "TRIP_EXPIRED"
    REQUEST_EXPIRED = "REQUEST_EXPIRED"
    REPORT_STATUS_CHANGED = "REPORT_STATUS_CHANGED"
    MODERATION_ACTION = "MODERATION_ACTION"
    MESSAGE_REMOVED = "MESSAGE_REMOVED"
    SETTINGS_CHANGED = "SETTINGS_CHANGED"
    FEATURE_FLAG_CHANGED = "FEATURE_FLAG_CHANGED"
    ADMIN_PII_VIEWED = "ADMIN_PII_VIEWED"


ACTOR_TYPE_ENUM: Final = Enum(
    ActorType,
    name="audit_logs_actor_type_enum",
    values_callable=lambda enum: [member.value for member in enum],
)


class AuditLog(Base, CreatedAtMixin):
    """One immutable record of a security-relevant action.

    ``metadata`` is mapped as ``payload`` because ``metadata`` is reserved on declarative
    classes. It must never contain PII or document contents (security.md §9).
    """

    __tablename__ = "audit_logs"
    # Ascending indexes: PostgreSQL scans b-trees in either direction, so the "newest first"
    # queries from database.md §2.9 are served without a DESC index.
    __table_args__ = (
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_actor_id_created_at", "actor_id", "created_at"),
        Index("ix_audit_logs_target", "target_type", "target_id"),
    )

    id: Mapped[UUID] = uuid_primary_key()
    actor_type: Mapped[ActorType] = mapped_column(ACTOR_TYPE_ENUM, nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_id: Mapped[UUID | None] = mapped_column(nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    request_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
