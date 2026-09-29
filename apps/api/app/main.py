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

from app.api.v1 import router as api_v1_router
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.core.errors import register_error_handlers
from app.core.health import router as health_router
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.core.openapi import install_custom_openapi
from app.core.redis import create_redis, ping_redis

log = structlog.get_logger("app.main")

OPENAPI_TAGS = [
    {"name": "platform", "description": "Public runtime configuration and feature flags."},
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
            allow_headers=["Authorization", "Content-Type", "X-Request-Id", "X-CSRF-Token"],
            expose_headers=["X-Request-Id"],
            max_age=600,
        )

    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(api_v1_router)
    install_custom_openapi(app)
    return app
