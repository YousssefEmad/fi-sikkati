"""Ratings, reports, blocks (BR-SAFE-*, OD-010/016)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import (
    AlreadyRatedError,
    ForbiddenError,
    NotFoundError,
    RatingWindowClosedError,
    ValidationAppError,
)
from app.core.events import EventPublisher, NoopEventPublisher, RatingSubmitted, ReviewRequested
from app.core.ids import uuid7
from app.core.lifecycle import BookingBridge, NoopBookingBridge
from app.core.rate_limit import RateLimit, RateLimiter
from app.core.security import keyed_hash
from app.modules.chat.models import Message
from app.modules.safety.models import (
    COMMENT_MAX_LENGTH,
    RATING_STAR_MAX,
    RATING_STAR_MIN,
    REPORT_DESCRIPTION_MAX,
    Rating,
    Report,
    ReportReason,
    ReportStatus,
    ReportTargetType,
    UserBlock,
)
from app.modules.safety.repository import SafetyRepository
from app.modules.trips.models import TripStatus


@dataclass(frozen=True, slots=True)
class RatingView:
    id: UUID
    trip_id: UUID
    rater_id: UUID
    ratee_id: UUID
    overall: int
    punctuality: int | None
    communication: int | None
    experience: int | None
    comment: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RatingSummaryView:
    user_id: UUID
    count: int
    average: float | None
    visible: bool


@dataclass(frozen=True, slots=True)
class ReportView:
    id: UUID
    reporter_id: UUID
    target_type: ReportTargetType
    target_id: UUID
    reason: ReportReason
    description: str | None
    status: ReportStatus
    created_at: datetime
    resolved_at: datetime | None


@dataclass(frozen=True, slots=True)
class BlockView:
    user_id: UUID
    display_name: str
    created_at: datetime


class SafetyService:
    def __init__(
        self,
        repository: SafetyRepository,
        settings: Settings,
        *,
        events: EventPublisher | None = None,
        bridge: BookingBridge | None = None,
        limiter: RateLimiter | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._events = events or NoopEventPublisher()
        self._bridge = bridge or NoopBookingBridge()
        self._limiter = limiter

    async def rate(
        self,
        *,
        rater_id: UUID,
        trip_id: UUID,
        ratee_id: UUID,
        overall: int,
        punctuality: int | None,
        communication: int | None,
        experience: int | None,
        comment: str | None,
    ) -> RatingView:
        _stars(overall, "overall")
        for name, value in (
            ("punctuality", punctuality),
            ("communication", communication),
            ("experience", experience),
        ):
            if value is not None:
                _stars(value, name)
        cleaned = _optional_text(comment, COMMENT_MAX_LENGTH, "comment")
        if rater_id == ratee_id:
            raise ValidationAppError("You cannot rate yourself.")
        trip = await self._repository.get_trip(trip_id)
        if trip is None or trip.status is not TripStatus.COMPLETED:
            raise NotFoundError("Trip not found.")
        if trip.completed_at is None:
            raise RatingWindowClosedError("This trip cannot be rated yet.")
        window = timedelta(days=self._settings.ratings_window_days)
        if datetime.now(UTC) - trip.completed_at > window:
            raise RatingWindowClosedError("The rating window for this trip has closed.")
        driver = trip.driver_id
        passengers = await self._bridge.passenger_ids(trip_id, include_pending=False)
        peers = {driver, *passengers}
        if rater_id not in peers or ratee_id not in peers:
            raise ForbiddenError("You can only rate people who shared this trip.")
        existing = await self._repository.get_rating_pair(trip_id, rater_id, ratee_id)
        if existing is not None:
            raise AlreadyRatedError("You already rated this person for this trip.")
        rating = Rating(
            id=uuid7(),
            trip_id=trip_id,
            rater_id=rater_id,
            ratee_id=ratee_id,
            overall=overall,
            punctuality=punctuality,
            communication=communication,
            experience=experience,
            comment=cleaned,
        )
        try:
            await self._repository.insert_rating(rating)
        except IntegrityError as exc:
            raise AlreadyRatedError("You already rated this person for this trip.") from exc
        await self._events.publish(
            RatingSubmitted(trip_id=trip_id, rater_id=rater_id, ratee_id=ratee_id)
        )
        return _rating_view(rating)

    async def summary(self, user_id: UUID) -> RatingSummaryView:
        count, average = await self._repository.summary(user_id)
        visible = count >= self._settings.ratings_min_count_to_display
        return RatingSummaryView(
            user_id=user_id,
            count=count if visible else 0,
            average=round(average, 2) if visible and average is not None else None,
            visible=visible,
        )

    async def report(
        self,
        *,
        reporter_id: UUID,
        target_type: ReportTargetType,
        target_id: UUID,
        reason: ReportReason,
        description: str | None,
        hash_secret: str,
    ) -> ReportView:
        cleaned = _optional_text(description, REPORT_DESCRIPTION_MAX, "description")
        if self._limiter is not None:
            limit = RateLimit.parse("reports", self._settings.reports_per_user_per_day)
            await self._limiter.enforce(limit, keyed_hash(str(reporter_id), hash_secret))
        report = Report(
            id=uuid7(),
            reporter_id=reporter_id,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            description=cleaned,
        )
        try:
            await self._repository.insert_report(report)
        except IntegrityError as exc:
            raise ValidationAppError("You already have an open report on this target.") from exc
        await self._events.publish(
            ReviewRequested(kind="REPORT", subject_user_id=reporter_id, report_id=report.id)
        )
        if target_type is ReportTargetType.MESSAGE:
            count = await self._repository.count_independent_message_reports(target_id)
            if count >= self._settings.reports_auto_hide_threshold:
                message = await self._repository.session.get(Message, target_id)
                if message is not None and message.deleted_at is None:
                    message.deleted_at = datetime.now(UTC)
        return _report_view(report)

    async def list_mine(
        self, reporter_id: UUID, *, before: tuple[datetime, UUID] | None, limit: int
    ) -> list[ReportView]:
        rows = await self._repository.list_mine(reporter_id, before=before, limit=limit)
        return [_report_view(row) for row in rows]

    async def block(self, blocker_id: UUID, blocked_id: UUID) -> None:
        if blocker_id == blocked_id:
            raise ValidationAppError("You cannot block yourself.")
        if await self._repository.get_user(blocked_id) is None:
            raise NotFoundError("User not found.")
        if await self._repository.is_blocked_either_way(blocker_id, blocked_id):
            existing = await self._repository.session.get(UserBlock, (blocker_id, blocked_id))
            if existing is not None:
                return
        self._repository.session.add(UserBlock(blocker_id=blocker_id, blocked_id=blocked_id))
        await self._repository.session.flush()

    async def unblock(self, blocker_id: UUID, blocked_id: UUID) -> None:
        deleted = await self._repository.remove_block(blocker_id, blocked_id)
        if deleted == 0:
            raise NotFoundError("Block not found.")

    async def list_blocks(self, blocker_id: UUID) -> list[BlockView]:
        rows = await self._repository.list_blocks(blocker_id)
        return [
            BlockView(user_id=uid, display_name=name, created_at=stamp) for uid, name, stamp in rows
        ]


class SafetyBlockChecker:
    """Implements :class:`app.core.lifecycle.BlockChecker`."""

    async def is_blocked_either_way(self, db: AsyncSession, a: UUID, b: UUID) -> bool:
        return await SafetyRepository(db).is_blocked_either_way(a, b)

    async def hidden_user_ids(self, db: AsyncSession, viewer_id: UUID) -> frozenset[UUID]:
        return await SafetyRepository(db).hidden_user_ids(viewer_id)


def _stars(value: int, field: str) -> None:
    if value < RATING_STAR_MIN or value > RATING_STAR_MAX:
        raise ValidationAppError(
            f"{field} must be between {RATING_STAR_MIN} and {RATING_STAR_MAX}."
        )


def _optional_text(value: str | None, max_length: int, field: str) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if len(trimmed) > max_length:
        raise ValidationAppError(f"{field} must be {max_length} characters or fewer.")
    return trimmed


def _rating_view(row: Rating) -> RatingView:
    return RatingView(
        id=row.id,
        trip_id=row.trip_id,
        rater_id=row.rater_id,
        ratee_id=row.ratee_id,
        overall=row.overall,
        punctuality=row.punctuality,
        communication=row.communication,
        experience=row.experience,
        comment=row.comment,
        created_at=row.created_at,
    )


def _report_view(row: Report) -> ReportView:
    return ReportView(
        id=row.id,
        reporter_id=row.reporter_id,
        target_type=row.target_type,
        target_id=row.target_id,
        reason=row.reason,
        description=row.description,
        status=row.status,
        created_at=row.created_at,
        resolved_at=row.resolved_at,
    )
