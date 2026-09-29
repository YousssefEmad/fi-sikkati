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
from app.core.logging import configure_logging

log = structlog.get_logger("app.worker")

WORKER_HEARTBEAT_KEY = "fisikkati:worker:heartbeat"
WORKER_HEARTBEAT_TTL_SECONDS = 120


async def heartbeat(ctx: dict[str, Any]) -> None:
    """Write a short-lived key so readiness probes can tell the worker is running."""
    await ctx["redis"].set(WORKER_HEARTBEAT_KEY, "1", ex=WORKER_HEARTBEAT_TTL_SECONDS)


async def on_startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, log_format=settings.log_format)
    log.info("worker_startup", env=settings.app_env)


async def on_shutdown(ctx: dict[str, Any]) -> None:
    log.info("worker_shutdown")


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(str(get_settings().redis_url))


class WorkerSettings:
    functions: list[Any] = []
    cron_jobs = [cron(heartbeat, second={0, 30}, run_at_startup=True)]
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = _redis_settings()
    max_tries = 5
    retry_jobs = True
    health_check_interval = 60
