"""Transactional email bodies: locale, escaping, no secrets in the plain-text shape."""

from __future__ import annotations

from app.modules.auth import emails


def test_verification_email_is_rtl_for_arabic() -> None:
    message = emails.verification_email(
        to="a@example.com", display_name="سارة", locale="ar", link="https://example/x"
    )
    assert "في سكتي" in message.subject
    assert 'dir="rtl"' in message.html_body
    assert "https://example/x" in message.text_body
    assert "https://example/x" in message.html_body


def test_html_escapes_the_display_name() -> None:
    message = emails.verification_email(
        to="a@example.com",
        display_name='<script>alert("x")</script>',
        locale="en",
        link="https://example/x",
    )
    assert "<script>" not in message.html_body
    assert "&lt;script&gt;" in message.html_body
    # The plain-text part is not HTML; the name appears as typed so a mail client will not parse it.
    assert "<script>" in message.text_body


def test_unsupported_locale_falls_back_to_arabic() -> None:
    message = emails.password_reset_email(
        to="a@example.com", display_name="Sara", locale="fr", link="https://example/x"
    )
    assert "في سكتي" in message.subject
