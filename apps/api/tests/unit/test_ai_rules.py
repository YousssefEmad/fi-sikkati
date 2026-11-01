from app.modules.ai.rules import interpret


def test_trip_intent_extracts_two_places() -> None:
    result = interpret("going from El Obour to Nasr City tomorrow morning")
    assert result.origin == "El Obour"
    assert result.destination == "Nasr City"


def test_faq_explains_that_this_is_not_a_taxi() -> None:
    result = interpret("how does this work?")
    assert "not a taxi" in result.answer.casefold()


def test_unknown_prompt_refuses_to_book() -> None:
    result = interpret("book me a car right now")
    assert "cannot create bookings" in result.answer.casefold()
