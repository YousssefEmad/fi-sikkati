# ruff: noqa: RUF001 — Arabic letters are the data, not Latin lookalikes.
"""Public display-name identity.

Two accounts must not share a name that looks the same once case, spacing, Arabic
spelling variants, digits, and diacritics are ignored. Near-duplicates (one extra
letter, or the same stem with a trailing mark) are rejected too.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

_ARABIC_FOLDS = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ة": "ه",
        "ؤ": "و",
        "ئ": "ي",
        "ء": "",
        "ـ": "",
    }
)
_SPACES = re.compile(r"\s+")
_NON_LETTERS = re.compile(r"[^\w\s]", flags=re.UNICODE)
_DIGITS = re.compile(r"\d+")
_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff]")

# Same stem with a tiny change still reads as the same person on a phone screen.
_SIMILARITY_FLOOR = 0.92


def display_name_key(value: str) -> str:
    """Stable comparison key for a public name. Empty when nothing readable remains."""
    folded = unicodedata.normalize("NFKD", value)
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    folded = _ZERO_WIDTH.sub("", folded)
    folded = folded.translate(_ARABIC_FOLDS)
    folded = folded.casefold()
    folded = _DIGITS.sub("", folded)
    folded = _NON_LETTERS.sub("", folded)
    return _SPACES.sub(" ", folded).strip()


def display_names_conflict(left: str, right: str) -> bool:
    """True when two keys would look like the same person to a rider."""
    if not left or not right:
        return False
    if left == right:
        return True
    shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
    if longer.startswith(shorter) and 0 < len(longer) - len(shorter) <= 2:
        return True
    if abs(len(left) - len(right)) > 2:
        return False
    return SequenceMatcher(None, left, right).ratio() >= _SIMILARITY_FLOOR
