"""Request correlation ids.

Every request gets an id (client-supplied ``X-Request-Id`` when it is well-formed, otherwise a
fresh UUID). The id is stored on ``request.state``, echoed in the response header and bound to
the structlog context so every log line during the request carries it (MEP §72).
"""

from __future__ import annotations

import re
import uuid

from starlette.requests import Request

REQUEST_ID_HEADER = "X-Request-Id"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._\-]{8,128}$")


def new_request_id() -> str:
    return str(uuid.uuid4())


def normalise_request_id(candidate: str | None) -> str:
    """Accept a client-provided id only when it is short and printable; never trust blindly."""
    if candidate and _VALID_REQUEST_ID.match(candidate):
        return candidate
    return new_request_id()


def get_request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else None
