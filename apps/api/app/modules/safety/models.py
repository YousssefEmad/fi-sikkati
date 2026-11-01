"""``ratings``, ``reports``, ``moderation_actions`` and ``user_blocks`` (database.md §2.7)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Final
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, CreatedAtMixin, TimestampMixin, uuid_primary_key

COMMENT_MAX_LENGTH = 500
REPORT_DESCRIPTION_MAX = 1000
RATING_STAR_MIN = 1
RATING_STAR_MAX = 5


class ReportTargetType(StrEnum):
    USER = "USER"
    TRIP = "TRIP"
    MESSAGE = "MESSAGE"


class ReportReason(StrEnum):
    SAFETY = "SAFETY"
    HARASSMENT = "HARASSMENT"
    SPAM = "SPAM"
    NO_SHOW = "NO_SHOW"
    FRAUD = "FRAUD"
    OTHER = "OTHER"


class ReportStatus(StrEnum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class ModerationActionType(StrEnum):
    WARN = "WARN"
    REMOVE_CONTENT = "REMOVE_CONTENT"
    SUSPEND_USER = "SUSPEND_USER"
    RESTORE_USER = "RESTORE_USER"
    CANCEL_TRIP = "CANCEL_TRIP"
    REVOKE_DRIVER = "REVOKE_DRIVER"


def _pg_enum(enum: type[StrEnum], name: str) -> Enum:
    return Enum(enum, name=name, values_callable=lambda members: [m.value for m in members])


REPORT_TARGET_ENUM: Final = _pg_enum(ReportTargetType, "reports_target_type_enum")
REPORT_REASON_ENUM: Final = _pg_enum(ReportReason, "reports_reason_enum")
REPORT_STATUS_ENUM: Final = _pg_enum(ReportStatus, "reports_status_enum")
MODERATION_ACTION_ENUM: Final = _pg_enum(ModerationActionType, "moderation_actions_action_enum")


class Rating(Base, CreatedAtMixin):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("trip_id", "rater_id", "ratee_id", name="uq_ratings_trip_pair"),
        CheckConstraint("rater_id <> ratee_id", name="rater_not_ratee"),
        CheckConstraint("overall BETWEEN 1 AND 5", name="overall_range"),
        CheckConstraint(
            "punctuality IS NULL OR punctuality BETWEEN 1 AND 5", name="punctuality_range"
        ),
        CheckConstraint(
            "communication IS NULL OR communication BETWEEN 1 AND 5", name="communication_range"
        ),
        CheckConstraint(
            "experience IS NULL OR experience BETWEEN 1 AND 5", name="experience_range"
        ),
        CheckConstraint("comment IS NULL OR char_length(comment) <= 500", name="comment_length"),
        Index("ix_ratings_ratee_id", "ratee_id"),
        Index("ix_ratings_trip_id", "trip_id"),
    )

    id: Mapped[UUID] = uuid_primary_key()
    trip_id: Mapped[UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="RESTRICT"), nullable=False
    )
    rater_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    ratee_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    overall: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    punctuality: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    communication: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    experience: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class Report(Base, TimestampMixin):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint(
            "description IS NULL OR char_length(description) <= 1000",
            name="description_length",
        ),
        Index(
            "uq_reports_open_target",
            "reporter_id",
            "target_type",
            "target_id",
            unique=True,
            postgresql_where=text("status IN ('OPEN', 'UNDER_REVIEW')"),
        ),
        Index("ix_reports_status_created", "status", "created_at"),
        Index("ix_reports_target", "target_type", "target_id"),
    )

    id: Mapped[UUID] = uuid_primary_key()
    reporter_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    target_type: Mapped[ReportTargetType] = mapped_column(REPORT_TARGET_ENUM, nullable=False)
    target_id: Mapped[UUID] = mapped_column(nullable=False)
    reason: Mapped[ReportReason] = mapped_column(REPORT_REASON_ENUM, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        REPORT_STATUS_ENUM,
        nullable=False,
        default=ReportStatus.OPEN,
        server_default=ReportStatus.OPEN.value,
    )
    resolved_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ModerationAction(Base, CreatedAtMixin):
    __tablename__ = "moderation_actions"
    __table_args__ = (Index("ix_moderation_actions_target_user_id", "target_user_id"),)

    id: Mapped[UUID] = uuid_primary_key()
    report_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("reports.id", ondelete="SET NULL"), nullable=True
    )
    actor_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    target_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    action: Mapped[ModerationActionType] = mapped_column(MODERATION_ACTION_ENUM, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )


class UserBlock(Base, TimestampMixin):
    """Unilateral and silent (BR-SAFE-05). Both directions hide the pair from each other."""

    __tablename__ = "user_blocks"
    __table_args__ = (
        CheckConstraint("blocker_id <> blocked_id", name="not_self"),
        UniqueConstraint("blocker_id", "blocked_id", name="uq_user_blocks_pair"),
        Index("ix_user_blocks_blocked_id", "blocked_id"),
    )

    blocker_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    blocked_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
