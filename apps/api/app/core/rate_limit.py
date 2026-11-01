"""Redis sliding-window rate limiting (security.md §7).

One Lua script does the whole decision atomically: drop timestamps that fell out of the window,
count what is left, and record the new hit only if the request is allowed. Because rejected
requests are not recorded, a client under attack cannot extend its own penalty indefinitely.

Keys are always derived from *hashed* identifiers (`keyed_hash`), so Redis never holds an email
address or an IP in clear text.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Final

from fastapi import Request
from redis.asyncio import Redis

from app.core.errors import RateLimitedError

KEY_PREFIX: Final = "rl"

# KEYS[1] = bucket key, ARGV = now_ms, window_ms, limit, member
# Returns {allowed, count, oldest_ms}
_SCRIPT: Final = """
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
local count = redis.call('ZCARD', KEYS[1])
if count >= limit then
  local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
  return {0, count, tonumber(oldest[2])}
end
redis.call('ZADD', KEYS[1], now, ARGV[4])
redis.call('PEXPIRE', KEYS[1], window)
return {1, count + 1, now}
"""


@dataclass(frozen=True, slots=True)
class RateLimit:
    """A named limit: ``limit`` events per ``window_seconds``."""

    name: str
    limit: int
    window_seconds: int

    def __post_init__(self) -> None:
        if self.limit < 1 or self.window_seconds < 1:
            msg = "rate limits must allow at least one event in at least one second"
            raise ValueError(msg)

    @classmethod
    def parse(cls, name: str, spec: str) -> RateLimit:
        """Build a limit from its configured ``"<events>/<window seconds>"`` form."""
        events, _, window = spec.partition("/")
        try:
            return cls(name=name, limit=int(events), window_seconds=int(window))
        except ValueError as exc:
            msg = f"invalid rate limit '{spec}' for {name}; expected '<events>/<seconds>'"
            raise ValueError(msg) from exc


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class RateLimiter:
    """Sliding-window limiter backed by one Redis sorted set per (limit, subject)."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._script = redis.register_script(_SCRIPT)

    async def check(self, limit: RateLimit, subject: str) -> RateLimitResult:
        """Record an attempt and report whether it is allowed. Never raises on Redis errors."""
        now_ms = int(time.time() * 1000)
        window_ms = limit.window_seconds * 1000
        key = f"{KEY_PREFIX}:{limit.name}:{subject}"
        raw = await self._script(
            keys=[key],
            args=[now_ms, window_ms, limit.limit, f"{now_ms}-{time.perf_counter_ns()}"],
        )
        allowed, count, oldest_ms = (int(part) for part in raw)
        if allowed:
            return RateLimitResult(
                allowed=True, remaining=max(limit.limit - count, 0), retry_after_seconds=0
            )
        retry_after_ms = max(oldest_ms + window_ms - now_ms, 1000)
        return RateLimitResult(
            allowed=False,
            remaining=0,
            retry_after_seconds=(retry_after_ms + 999) // 1000,
        )

    async def enforce(self, limit: RateLimit, subject: str) -> None:
        """Raise :class:`RateLimitedError` with ``Retry-After`` when the limit is exceeded."""
        result = await self.check(limit, subject)
        if result.allowed:
            return
        raise RateLimitedError(
            "Too many attempts. Please wait before trying again.",
        ).with_retry_after(result.retry_after_seconds)


def get_rate_limiter(request: Request) -> RateLimiter:
    """FastAPI dependency returning the limiter created during application startup."""
    limiter = getattr(request.app.state, "rate_limiter", None)
    if not isinstance(limiter, RateLimiter):  # pragma: no cover — wiring error
        msg = "RateLimiter is not initialised on app.state"
        raise TypeError(msg)
    return limiter


def client_ip(request: Request) -> str:
    """Best-effort client IP for rate-limit keys.

    Only the left-most entry of ``X-Forwarded-For`` set by our own reverse proxy is trusted; the
    value is always hashed before it is used as a key, so a spoofed header can at worst give an
    attacker a different bucket, never read another one.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"
