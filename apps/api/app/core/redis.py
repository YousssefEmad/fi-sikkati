"""Redis client lifecycle.

Redis is used for caching, rate limiting, job queues and pub/sub only — never as a source of
truth (MEP §36).
"""

from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import Settings


def create_redis(settings: Settings) -> Redis:
    # Slightly higher timeouts for serverless + managed Redis (Upstash / Neon companions).
    client: Redis = Redis.from_url(
        str(settings.redis_url),
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
        retry_on_timeout=True,
    )
    return client


async def ping_redis(client: Redis) -> None:
    """Raise if Redis is unreachable (used by readiness checks)."""
    await client.ping()
