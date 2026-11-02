"""Rate-limit spec parsing (security.md §7)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.rate_limit import RateLimit, RateLimiter


def test_parse_splits_events_and_window() -> None:
    limit = RateLimit.parse("auth_login_ip", "10/900")
    assert limit.name == "auth_login_ip"
    assert limit.limit == 10
    assert limit.window_seconds == 900


def test_parse_rejects_a_malformed_spec() -> None:
    with pytest.raises(ValueError, match="invalid rate limit"):
        RateLimit.parse("auth_login_ip", "ten-per-hour")


def test_limit_must_allow_at_least_one_event() -> None:
    with pytest.raises(ValueError, match="at least one"):
        RateLimit(name="x", limit=0, window_seconds=1)


@pytest.mark.asyncio
async def test_check_allows_when_redis_is_down() -> None:
    redis = MagicMock()
    script = AsyncMock(side_effect=RedisConnectionError("down"))
    redis.register_script.return_value = script
    limiter = RateLimiter(redis)
    result = await limiter.check(RateLimit(name="auth_login_ip", limit=5, window_seconds=60), "x")
    assert result.allowed is True
