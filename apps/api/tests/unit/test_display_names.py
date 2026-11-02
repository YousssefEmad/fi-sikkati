"""Display names that look the same must share one key or fail the conflict check."""

from app.modules.users.names import display_name_key, display_names_conflict


def test_arabic_spelling_variants_collapse() -> None:
    assert display_name_key("يُوسُف") == display_name_key("يوسف")
    assert display_name_key("فاطمة") == display_name_key("فاطمه")
    assert display_name_key("مصطفى") == display_name_key("مصطفي")


def test_latin_case_and_spacing_collapse() -> None:
    assert display_name_key("  Youssef  ") == display_name_key("youssef")
    assert display_name_key("Youssef.") == display_name_key("youssef")


def test_digits_do_not_make_a_new_name() -> None:
    assert display_name_key("يوسف") == display_name_key("يوسف2")
    assert display_name_key("Sara") == display_name_key("Sara99")
    assert display_names_conflict(display_name_key("يوسف"), display_name_key("يوسف2"))


def test_near_duplicates_conflict() -> None:
    assert display_names_conflict("يوسف", "يوسفي")
    assert display_names_conflict("nour", "nourr")


def test_different_names_stay_apart() -> None:
    assert display_name_key("محمد") != display_name_key("محمود")
    assert display_name_key("يوسف") != display_name_key("youssef")
    assert not display_names_conflict(display_name_key("محمد"), display_name_key("محمود"))
