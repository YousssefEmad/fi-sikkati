"""Egyptian mobile numbers become E.164 before they are stored."""

import pytest

from app.modules.users.phones import normalize_phone


def test_local_egyptian_mobile_gains_the_country_code() -> None:
    assert normalize_phone("01012345678") == "+201012345678"
    assert normalize_phone("011 1234 5678") == "+201112345678"
    assert normalize_phone("015-1234-5678") == "+201512345678"


def test_international_numbers_stay_international() -> None:
    assert normalize_phone("+201012345678") == "+201012345678"
    assert normalize_phone("00201012345678") == "+201012345678"


def test_landlines_and_short_numbers_are_rejected() -> None:
    with pytest.raises(ValueError):
        normalize_phone("0212345678")
    with pytest.raises(ValueError):
        normalize_phone("12345")
