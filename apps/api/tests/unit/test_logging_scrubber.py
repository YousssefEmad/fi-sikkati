from __future__ import annotations

from app.core.logging import scrub_sensitive_data


def test_sensitive_keys_are_redacted_recursively() -> None:
    event = {
        "event": "login",
        "password": "hunter2",
        "user": {"email": "a@b.c", "display_name": "Salma", "phone_e164": "+20100"},
        "headers": [{"authorization": "Bearer x"}],
        "refresh_token": "abc",
    }
    scrubbed = scrub_sensitive_data(None, "info", event)
    assert scrubbed["password"] == "[REDACTED]"
    assert scrubbed["refresh_token"] == "[REDACTED]"
    assert scrubbed["user"]["email"] == "[REDACTED]"
    assert scrubbed["user"]["phone_e164"] == "[REDACTED]"
    assert scrubbed["user"]["display_name"] == "Salma"
    assert scrubbed["headers"][0]["authorization"] == "[REDACTED]"
    assert scrubbed["event"] == "login"


def test_long_values_are_truncated() -> None:
    scrubbed = scrub_sensitive_data(None, "info", {"body": "x" * 5000})
    assert scrubbed["body"].endswith("…[truncated]")
    assert len(scrubbed["body"]) < 2100
