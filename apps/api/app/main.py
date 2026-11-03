"""FastAPI application factory.

Run with ``uvicorn app.main:create_app --factory`` so importing this module has no side effects
(tests build their own instance with explicit settings).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import router as api_v1_router
from app.core.authz.ports import bind_identity_loader, bind_session_revoker
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.core.email import LoggingEmailSender, SmtpEmailSender
from app.modules.files.database_storage import DatabaseObjectStorage
from app.core.errors import register_error_handlers
from app.core.events import DomainEvent, EventDispatcher, EventPublisher, bind_event_dispatcher
from app.core.health import router as health_router
from app.core.lifecycle import (
    BookingBridge,
    CompositeDeletionGuard,
    bind_block_checker,
    bind_booking_bridge_factory,
    bind_cancellation_stats,
    bind_deletion_guard,
)
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.core.openapi import install_custom_openapi
from app.core.rate_limit import RateLimiter
from app.core.redis import create_redis, ping_redis
from app.core.security import AccessTokenService, PasswordService
from app.core.sms import NullSmsSender, TwilioSmsSender
from app.modules.auth.service import make_session_revoker
from app.modules.bookings.dependencies import (
    BookingCancellationStats,
    BookingDeletionGuard,
    booking_service_for,
)
from app.modules.chat.service import chat_service_for
from app.modules.files.s3 import MinioObjectStorage
from app.modules.maps.fake import FakeMapProvider
from app.modules.maps.mapbox import MapboxMapProvider
from app.modules.notifications.service import notification_service_for
from app.modules.safety.dependencies import safety_block_checker
from app.modules.trips.dependencies import TripDeletionGuard
from app.modules.users.service import make_identity_loader

log = structlog.get_logger("app.main")


def build_event_dispatcher(
    settings: Settings, limiter: RateLimiter | None = None
) -> EventDispatcher:
    """Subscribe chat and notifications to domain events. Composition root only."""
    dispatcher = EventDispatcher()

    async def on_chat(db: AsyncSession, event: DomainEvent) -> None:
        service = chat_service_for(
            db, settings, events=EventPublisher(dispatcher, db), limiter=limiter
        )
        await service.handle_event(event)

    async def on_notify(db: AsyncSession, event: DomainEvent) -> None:
        await notification_service_for(db, settings).handle_event(event)

    dispatcher.subscribe_all(on_chat)
    dispatcher.subscribe_all(on_notify)
    return dispatcher


OPENAPI_TAGS = [
    {"name": "platform", "description": "Public runtime configuration and feature flags."},
    {"name": "auth", "description": "Registration, sign-in, sessions and password management."},
    {"name": "users", "description": "The signed-in account, its profile and public profiles."},
    {"name": "verification", "description": "Identity and driver document submission."},
    {
        "name": "vehicles",
        "description": "The signed-in user's vehicles and registration documents.",
    },
    {"name": "maps", "description": "Place search and server-computed route previews."},
    {"name": "pricing", "description": "Suggested contribution estimates (no payments)."},
    {"name": "trips", "description": "Driver trip lifecycle."},
    {"name": "search", "description": "Passenger search over published trips."},
    {"name": "bookings", "description": "Join requests and seat reservation."},
    {
        "name": "chat",
        "description": "Trip conversations between the driver and accepted passengers.",
    },
    {"name": "notifications", "description": "In-app notifications and channel preferences."},
    {"name": "safety", "description": "Ratings, reports, blocks and the safety centre."},
    {
        "name": "admin",
        "description": "Administrator review queues and the operations dashboard (internal).",
    },
    {"name": "ai", "description": "In-app assistant (read-only tools, feature-flagged)."},
]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(level=settings.log_level, log_format=settings.log_format)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database = Database(settings)
        redis = create_redis(settings)
        app.state.database = database
        app.state.redis = redis
        app.state.health_checks = {
            "database": database.ping,
            "redis": lambda: ping_redis(redis),
        }
        # Expensive to build and stateless once built: one instance per process.
        app.state.password_service = PasswordService(settings)
        app.state.access_token_service = AccessTokenService(settings)
        app.state.rate_limiter = RateLimiter(redis)
        app.state.email_sender = (
            SmtpEmailSender(settings) if settings.smtp_configured else LoggingEmailSender()
        )
        app.state.sms_sender = (
            TwilioSmsSender(settings) if settings.sms_configured else NullSmsSender()
        )
        app.state.object_storage = (
            MinioObjectStorage(settings) if settings.s3_configured else DatabaseObjectStorage(settings)
        )
        if settings.mapbox_access_token:
            app.state.map_provider = MapboxMapProvider(settings)
        else:
            app.state.map_provider = FakeMapProvider()
        bind_deletion_guard(
            app.state,
            CompositeDeletionGuard((TripDeletionGuard(), BookingDeletionGuard())),
        )
        bind_cancellation_stats(app.state, BookingCancellationStats())
        bind_block_checker(app.state, safety_block_checker())
        dispatcher = build_event_dispatcher(settings, limiter=app.state.rate_limiter)
        bind_event_dispatcher(app.state, dispatcher)

        def _booking_bridge(session: AsyncSession) -> BookingBridge:
            return booking_service_for(session, settings, dispatcher=dispatcher)

        bind_booking_bridge_factory(app.state, _booking_bridge)
        # Composition root: the authorization layer reaches module data only through these
        # (app/core/authz/ports.py).
        bind_identity_loader(app.state, make_identity_loader(settings))
        bind_session_revoker(app.state, make_session_revoker())
        log.info("startup", env=settings.app_env, version=settings.api_version)
        try:
            yield
        finally:
            await redis.aclose()
            await database.dispose()
            log.info("shutdown")

    app = FastAPI(
        title="Fi Sikkati API",
        version="0.1.0",
        description=(
            "Community ride-sharing and route-matching platform. "
            "Drivers publish planned trips; passengers find people already going their way."
        ),
        openapi_url="/api/v1/openapi.json" if settings.docs_enabled else None,
        docs_url="/api/v1/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.state.settings = settings

    # Order matters: outermost first. Security headers wrap everything, then request context.
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    if settings.cors_origin_strings:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_strings,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "X-Request-Id",
                "X-CSRF-Token",
                "If-Match",
                "Idempotency-Key",
            ],
            expose_headers=["X-Request-Id"],
            max_age=600,
        )

    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(api_v1_router)
    install_custom_openapi(app)
    return app
