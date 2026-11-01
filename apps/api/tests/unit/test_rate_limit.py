"""Rate-limit spec parsing (security.md §7)."""

from __future__ import annotations

import pytest

from app.core.rate_limit import RateLimit


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
