"""SQL for ratings, reports, blocks and moderation."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.safety.models import (
    ModerationAction,
    Rating,
    Report,
    ReportStatus,
    ReportTargetType,
    UserBlock,
)
from app.modules.trips.models import Trip
from app.modules.users.models import User, UserProfile


class SafetyRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @property
    def session(self) -> AsyncSession:
        return self._db

    async def insert_rating(self, rating: Rating) -> None:
        async with self._db.begin_nested():
            self._db.add(rating)
            await self._db.flush()

    async def get_rating_pair(self, trip_id: UUID, rater_id: UUID, ratee_id: UUID) -> Rating | None:
        result = await self._db.execute(
            select(Rating).where(
                Rating.trip_id == trip_id,
                Rating.rater_id == rater_id,
                Rating.ratee_id == ratee_id,
            )
        )
        return result.scalar_one_or_none()

    async def summary(self, user_id: UUID) -> tuple[int, float | None]:
        row = await self._db.execute(
            select(func.count(), func.avg(Rating.overall)).where(Rating.ratee_id == user_id)
        )
        found = row.one()
        count = int(found[0] or 0)
        average = float(found[1]) if found[1] is not None else None
        return count, average

    async def insert_report(self, report: Report) -> None:
        async with self._db.begin_nested():
            self._db.add(report)
            await self._db.flush()

    async def get_report(self, report_id: UUID) -> Report | None:
        return await self._db.get(Report, report_id)

    async def list_mine(
        self, reporter_id: UUID, *, before: tuple[datetime, UUID] | None, limit: int
    ) -> list[Report]:
        query = select(Report).where(Report.reporter_id == reporter_id)
        if before is not None:
            stamp, ident = before
            query = query.where(
                (Report.created_at < stamp) | ((Report.created_at == stamp) & (Report.id < ident))
            )
        result = await self._db.execute(
            query.order_by(Report.created_at.desc(), Report.id.desc()).limit(limit)
        )
        return list(result.scalars())

    async def list_queue(
        self, *, status: ReportStatus | None, page: int, page_size: int
    ) -> tuple[list[Report], int]:
        query = select(Report)
        count_query = select(func.count()).select_from(Report)
        if status is not None:
            query = query.where(Report.status == status)
            count_query = count_query.where(Report.status == status)
        total = int(await self._db.scalar(count_query) or 0)
        result = await self._db.execute(
            query.order_by(Report.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return list(result.scalars()), total

    async def count_independent_message_reports(self, message_id: UUID) -> int:
        value = await self._db.scalar(
            select(func.count(func.distinct(Report.reporter_id)))
            .select_from(Report)
            .where(
                Report.target_type == ReportTargetType.MESSAGE,
                Report.target_id == message_id,
                Report.status.in_((ReportStatus.OPEN, ReportStatus.UNDER_REVIEW)),
            )
        )
        return int(value or 0)

    async def is_blocked_either_way(self, a: UUID, b: UUID) -> bool:
        found = await self._db.scalar(
            select(UserBlock.blocker_id).where(
                or_(
                    (UserBlock.blocker_id == a) & (UserBlock.blocked_id == b),
                    (UserBlock.blocker_id == b) & (UserBlock.blocked_id == a),
                )
            )
        )
        return found is not None

    async def hidden_user_ids(self, viewer_id: UUID) -> frozenset[UUID]:
        outgoing = await self._db.execute(
            select(UserBlock.blocked_id).where(UserBlock.blocker_id == viewer_id)
        )
        incoming = await self._db.execute(
            select(UserBlock.blocker_id).where(UserBlock.blocked_id == viewer_id)
        )
        return frozenset(outgoing.scalars()) | frozenset(incoming.scalars())

    async def list_blocks(self, blocker_id: UUID) -> list[tuple[UUID, str, datetime]]:
        result = await self._db.execute(
            select(UserBlock.blocked_id, UserProfile.display_name, UserBlock.created_at)
            .join(UserProfile, UserProfile.user_id == UserBlock.blocked_id)
            .where(UserBlock.blocker_id == blocker_id)
            .order_by(UserBlock.created_at.desc())
        )
        return [(row[0], str(row[1]), row[2]) for row in result]

    async def add_block(self, blocker_id: UUID, blocked_id: UUID) -> None:
        self._db.add(UserBlock(blocker_id=blocker_id, blocked_id=blocked_id))
        await self._db.flush()

    async def remove_block(self, blocker_id: UUID, blocked_id: UUID) -> int:
        result = await self._db.execute(
            delete(UserBlock).where(
                UserBlock.blocker_id == blocker_id, UserBlock.blocked_id == blocked_id
            )
        )
        return int(result.rowcount or 0) if isinstance(result, CursorResult) else 0

    async def get_user(self, user_id: UUID) -> User | None:
        return await self._db.get(User, user_id)

    async def get_trip(self, trip_id: UUID) -> Trip | None:
        return await self._db.get(Trip, trip_id)

    async def insert_action(self, action: ModerationAction) -> None:
        self._db.add(action)
        await self._db.flush()

    async def display_names(self, user_ids: Sequence[UUID]) -> dict[UUID, str]:
        if not user_ids:
            return {}
        result = await self._db.execute(
            select(UserProfile.user_id, UserProfile.display_name).where(
                UserProfile.user_id.in_(tuple(user_ids))
            )
        )
        return {row[0]: str(row[1]) for row in result}
