"""Small HTTP helpers for reading what the API put on the wire (api.md §3: problem+json)."""

from __future__ import annotations

from httpx import Response


def set_cookies(response: Response) -> dict[str, dict[str, str]]:
    """Parse ``Set-Cookie`` headers into ``{name: {"value": …, attribute: value}}``.

    Attribute names are lower-cased and flags (``Secure``, ``HttpOnly``) map to ``""``, so a test
    asserts presence with ``"secure" in cookie``.
    """
    cookies: dict[str, dict[str, str]] = {}
    for header in response.headers.get_list("set-cookie"):
        first, *attributes = (part.strip() for part in header.split(";"))
        name, _, value = first.partition("=")
        parsed = {"value": value}
        for attribute in attributes:
            key, _, attribute_value = attribute.partition("=")
            parsed[key.lower()] = attribute_value
        cookies[name] = parsed
    return cookies


def error_code(response: Response) -> str:
    body = response.json()
    assert "code" in body, body
    code: str = body["code"]
    return code


def field_errors(response: Response) -> dict[str, str]:
    """``{field: code}`` from a validation error body."""
    return {item["field"]: item["code"] for item in response.json().get("errors") or []}
