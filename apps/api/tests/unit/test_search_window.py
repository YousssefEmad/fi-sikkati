from __future__ import annotations

from datetime import date, time

import pytest

from app.core.errors import ValidationAppError
from app.modules.search.service import resolve_window


def test_explicit_from_to_uses_cairo_and_midpoint() -> None:
    window = resolve_window(
        day=date(2026, 10, 3),
        clock=None,
        time_from=time(7, 0),
        time_to=time(9, 0),
        default_window_minutes=60,
    )
    assert window.end > window.start
    assert window.start < window.requested_at < window.end


def test_clock_applies_default_plus_minus_window() -> None:
    window = resolve_window(
        day=date(2026, 10, 3),
        clock=time(8, 0),
        time_from=None,
        time_to=None,
        default_window_minutes=60,
    )
    assert (window.end - window.start).total_seconds() == 2 * 60 * 60


def test_date_only_covers_the_cairo_calendar_day() -> None:
    window = resolve_window(
        day=date(2026, 10, 3),
        clock=None,
        time_from=None,
        time_to=None,
        default_window_minutes=60,
    )
    assert (window.end - window.start).total_seconds() > 20 * 60 * 60


def test_half_open_time_bounds_are_rejected() -> None:
    with pytest.raises(ValidationAppError):
        resolve_window(
            day=date(2026, 10, 3),
            clock=None,
            time_from=time(8, 0),
            time_to=None,
            default_window_minutes=60,
        )
