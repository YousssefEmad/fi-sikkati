"""Turn a typed phone number into the E.164 value we store."""

from __future__ import annotations

import re

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")
_EGYPT_LOCAL = re.compile(r"^01[0125]\d{8}$")


def normalize_phone(value: str) -> str:
    """Accept ``01xxxxxxxxx`` and international numbers. Reject anything else."""
    compact = re.sub(r"[\s\-()]", "", value.strip())
    if compact.startswith("00"):
        compact = f"+{compact[2:]}"
    if _EGYPT_LOCAL.fullmatch(compact):
        compact = f"+20{compact[1:]}"
    elif compact.startswith("20") and not compact.startswith("+"):
        compact = f"+{compact}"
    if _E164.fullmatch(compact):
        return compact
    msg = "Enter a mobile number like 01xxxxxxxxx."
    raise ValueError(msg)
