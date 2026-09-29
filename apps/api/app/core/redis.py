"""Redis client lifecycle.

Redis is used for caching, rate limiting, job queues and pub/sub only — never as a source of
truth (MEP §36).
"""

from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import Settings


def create_redis(settings: Settings) -> Redis:
    client: Redis = Redis.from_url(
        str(settings.redis_url),
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=30,
    )
    return client


async def ping_redis(client: Redis) -> None:
    """Raise if Redis is unreachable (used by readiness checks)."""
    await client.ping()
