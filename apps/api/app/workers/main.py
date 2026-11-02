"""arq worker settings.

Run with ``uv run arq app.workers.main.WorkerSettings``. Phase 1 registers only a heartbeat cron
that lets ``/health/ready?deep=1`` (Phase 11) and operators confirm the worker is alive. Module
jobs are appended to ``functions`` as phases land.
"""

from __future__ import annotations

from typing import Any

import structlog
from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.database import Database
from app.core.email import LoggingEmailSender, SmtpEmailSender
from app.core.events import EventPublisher
from app.core.logging import configure_logging
from app.main import build_event_dispatcher
from app.modules.audit.service import AuditLogWriter
from app.modules.bookings.dependencies import booking_service_for
from app.modules.chat.service import chat_service_for
from app.modules.files.repository import FileRepository
from app.modules.files.s3 import MinioObjectStorage
from app.modules.files.service import FileService
from app.modules.maps.fake import FakeMapProvider
from app.modules.notifications.service import notification_service_for
from app.modules.pricing.repository import PricingRepository
from app.modules.pricing.service import PricingService
from app.modules.trips.repository import TripRepository
from app.modules.trips.service import TripService

log = structlog.get_logger("app.worker")

WORKER_HEARTBEAT_KEY = "fisikkati:worker:heartbeat"
WORKER_HEARTBEAT_TTL_SECONDS = 120


async def heartbeat(ctx: dict[str, Any]) -> None:
    """Write a short-lived key so readiness probes can tell the worker is running."""
    await ctx["redis"].set(WORKER_HEARTBEAT_KEY, "1", ex=WORKER_HEARTBEAT_TTL_SECONDS)


async def purge_expired_documents(ctx: dict[str, Any]) -> int:
    """BR-VER-06: delete private objects whose retention window has elapsed."""
    del ctx
    settings = get_settings()
    database = Database(settings)
    try:
        async with database.session_factory() as session:
            service = FileService(
                FileRepository(session),
                MinioObjectStorage(settings),
                settings,
                AuditLogWriter(session),
            )
            purged = await service.purge_due()
            await session.commit()
    finally:
        await database.dispose()
    log.info("documents_purged", count=purged)
    return purged


async def expire_and_complete_trips(ctx: dict[str, Any]) -> dict[str, int]:
    """OD-017: expire unpublished trips and auto-complete stale in-progress ones."""
    del ctx
    settings = get_settings()
    database = Database(settings)
    expired = completed = join_expired = 0
    try:
        async with database.session_factory() as session:
            dispatcher = build_event_dispatcher(settings)
            bookings = booking_service_for(session, settings, dispatcher=dispatcher)
            service = TripService(
                TripRepository(session),
                FakeMapProvider(),
                PricingService(PricingRepository(session)),
                settings,
                bridge=bookings,
                events=EventPublisher(dispatcher, session),
            )
            expired = await service.expire_due()
            completed = await service.auto_complete_due()
            join_expired = await bookings.expire_pending()
            await session.commit()
    finally:
        await database.dispose()
    log.info("trips_lifecycle", expired=expired, completed=completed, join_expired=join_expired)
    return {"expired": expired, "completed": completed, "joinExpired": join_expired}


async def purge_yesterdays_trips(ctx: dict[str, Any]) -> int:
    """Drop finished trips from before today (Cairo) and their trip chat."""
    del ctx
    settings = get_settings()
    database = Database(settings)
    purged = 0
    try:
        async with database.session_factory() as session:
            service = TripService(
                TripRepository(session),
                FakeMapProvider(),
                PricingService(PricingRepository(session)),
                settings,
            )
            purged = await service.purge_yesterdays_finished()
            await session.commit()
    finally:
        await database.dispose()
    log.info("trips_purged", count=purged)
    return purged


async def dispatch_notification_emails(ctx: dict[str, Any]) -> int:
    del ctx
    settings = get_settings()
    database = Database(settings)
    sent = 0
    try:
        async with database.session_factory() as session:
            service = notification_service_for(session, settings)
            sender = (
                SmtpEmailSender(settings) if settings.smtp_configured else LoggingEmailSender()
            )
            sent = await service.dispatch_pending_emails(sender)
            await session.commit()
    finally:
        await database.dispose()
    log.info("notification_emails_sent", count=sent)
    return sent


async def trip_reminders_and_chat_close(ctx: dict[str, Any]) -> dict[str, int]:
    del ctx
    settings = get_settings()
    database = Database(settings)
    cadence: dict[str, int] = {}
    closed = 0
    try:
        async with database.session_factory() as session:
            cadence = await notification_service_for(session, settings).send_trip_cadence()
            closed = await chat_service_for(session, settings).close_completed()
            await session.commit()
    finally:
        await database.dispose()
    log.info("trip_cadence", **cadence, conversationsClosed=closed)
    return {**cadence, "conversationsClosed": closed}


async def on_startup(ctx: dict[str, Any]) -> None:
    del ctx
    settings = get_settings()
    configure_logging(level=settings.log_level, log_format=settings.log_format)
    log.info("worker_startup", env=settings.app_env)


async def on_shutdown(ctx: dict[str, Any]) -> None:
    log.info("worker_shutdown")


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(str(get_settings().redis_url))


class WorkerSettings:
    functions: list[Any] = [
        purge_expired_documents,
        expire_and_complete_trips,
        purge_yesterdays_trips,
        dispatch_notification_emails,
        trip_reminders_and_chat_close,
    ]
    cron_jobs = [
        cron(heartbeat, second={0, 30}, run_at_startup=True),
        cron(purge_expired_documents, hour={3}, minute={15}),
        # 00:20 Africa/Cairo ≈ 22:20 UTC (winter). Finished trips from prior days go away.
        cron(purge_yesterdays_trips, hour={22}, minute={20}),
        cron(expire_and_complete_trips, minute={0, 15, 30, 45}),
        cron(dispatch_notification_emails, minute={2, 7, 12, 17, 22, 27, 32, 37, 42, 47, 52, 57}),
        cron(trip_reminders_and_chat_close, minute={5, 20, 35, 50}),
    ]
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = _redis_settings()
    max_tries = 5
    retry_jobs = True
    health_check_interval = 60
