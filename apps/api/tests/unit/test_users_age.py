"""Account-age arithmetic (BR-ACC-08)."""

from __future__ import annotations

from datetime import date

from app.modules.users.service import age_in_years


def test_age_on_birthday() -> None:
    assert age_in_years(date(2000, 6, 15), date(2018, 6, 15)) == 18


def test_age_the_day_before_birthday() -> None:
    assert age_in_years(date(2000, 6, 15), date(2018, 6, 14)) == 17


def test_leap_day_birthday_in_a_common_year() -> None:
    # Born 29 February 2004; on 28 February 2022 they are still 17.
    assert age_in_years(date(2004, 2, 29), date(2022, 2, 28)) == 17
    assert age_in_years(date(2004, 2, 29), date(2022, 3, 1)) == 18
