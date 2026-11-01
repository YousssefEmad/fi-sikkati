"""Opaque keyset cursors shared by every cursor-paginated list (api.md §1)."""

from __future__ import annotations

import base64
from datetime import datetime
from uuid import UUID


def encode_cursor(stamp: datetime, ident: UUID) -> str:
    raw = f"{stamp.isoformat()}|{ident}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(value: str | None) -> tuple[datetime, UUID] | None:
    """``None`` for a missing *or malformed* cursor: a bad cursor simply restarts the list."""
    if not value:
        return None
    try:
        decoded = base64.urlsafe_b64decode(value.encode()).decode()
        stamp, _, ident = decoded.partition("|")
        return datetime.fromisoformat(stamp), UUID(ident)
    except (ValueError, UnicodeError):
        return None
