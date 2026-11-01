"""Deterministic FAQ + trip-intent parser (OD-025: rules provider)."""

from __future__ import annotations

import re
from dataclasses import dataclass

PLACES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("El Obour", ("obour", "العبور", "العبور")),
    ("Nasr City", ("nasr", "مدينة نصر", "نصر")),
    ("Downtown", ("downtown", "وسط البلد", "التحرير")),
    ("New Cairo", ("new cairo", "التجمع", "القاهرة الجديدة")),
    ("6th of October", ("october", "اكتوبر", "أكتوبر")),
    ("Maadi", ("maadi", "المعادي")),
    ("Heliopolis", ("heliopolis", "مصر الجديدة")),
    ("Cairo", ("cairo", "القاهرة")),
)

FAQ: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("how it works", "ازاي", "كيف يعمل", "how does"),
        "A driver publishes a trip they already plan to make. You search by pickup, drop-off "
        "and time, request a seat, and chat after the driver accepts. This is not a taxi app.",
    ),
    (
        ("verif", "تحقق", "هوية", "identity"),
        "Passengers verify identity before the first join request. Drivers add a licence and "
        "vehicle documents. An admin reviews both queues.",
    ),
    (
        ("safe", "أمان", "سلامة", "report", "بلاغ"),
        "You can report a user, trip or message, and block someone silently. We never claim "
        "guaranteed physical safety and we do not connect to emergency services.",
    ),
    (
        ("pay", "سعر", "فلوس", "price", "cash"),
        "The shown amount is a suggested contribution. No money moves through Fi Sikkati in "
        "this version — settle in cash with the driver if you both agree.",
    ),
    (
        ("cancel", "إلغاء", "الغاء"),
        "You can cancel a pending request any time. After acceptance, late cancellations are "
        "counted. Drivers can cancel a trip; passengers are notified.",
    ),
)


@dataclass(frozen=True, slots=True)
class RuleResult:
    answer: str
    origin: str | None = None
    destination: str | None = None


def interpret(message: str) -> RuleResult:
    lowered = message.casefold()
    origin, destination = _places(lowered)
    if origin and destination and origin != destination:
        return RuleResult(
            answer=(
                f"I can look for trips from {origin} toward {destination}. "
                "Open search with these places — I never book a seat for you."
            ),
            origin=origin,
            destination=destination,
        )
    for needles, answer in FAQ:
        if any(needle in lowered for needle in needles):
            return RuleResult(answer=answer)
    return RuleResult(
        answer=(
            "I can explain how Fi Sikkati works, verification, safety, pricing, or help you "
            "phrase a search. I cannot create bookings, approve drivers, or change records."
        )
    )


_ROUTE_PLACE_COUNT = 2


def _places(text: str) -> tuple[str | None, str | None]:
    found: list[str] = []
    for label, aliases in PLACES:
        if any(re.search(re.escape(alias).casefold(), text) for alias in aliases):
            found.append(label)
        if len(found) == _ROUTE_PLACE_COUNT:
            break
    if len(found) == _ROUTE_PLACE_COUNT:
        return found[0], found[1]
    if len(found) == 1:
        return found[0], None
    return None, None
