# ruff: noqa: RUF001 — Arabic letters are the data, not Latin lookalikes.
"""Public display-name identity.

Two accounts must not share a name that looks the same once case, spacing, Arabic
spelling variants, and diacritics are ignored.
"""

from __future__ import annotations

import re
import unicodedata

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
_PUNCTUATION = re.compile(r"[^\w\s]", flags=re.UNICODE)


def display_name_key(value: str) -> str:
    """Stable comparison key for a public name. Empty when nothing readable remains."""
    folded = unicodedata.normalize("NFKD", value)
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    folded = folded.translate(_ARABIC_FOLDS)
    folded = folded.casefold()
    folded = _PUNCTUATION.sub("", folded)
    return _SPACES.sub(" ", folded).strip()
