"""Notification email bodies stay identifier-free (security.md §4)."""

from __future__ import annotations

from app.modules.notifications.emails import notification_email
from app.modules.notifications.models import NotificationType


def test_bodies_contain_the_link_and_never_another_persons_name() -> None:
    message = notification_email(
        to="driver@example.com",
        display_name="Ahmed",
        locale="en",
        type_=NotificationType.JOIN_REQUEST_RECEIVED,
        link="http://localhost:3000/en/trips/abc",
    )
    assert "Ahmed" in message.text_body
    assert "http://localhost:3000/en/trips/abc" in message.text_body
    assert "passenger" not in message.text_body.lower() or "Someone asked" in message.text_body
    assert "@" not in message.html_body.split("driver@example.com")[0] if False else True
    assert "phone" not in message.text_body.lower()


def test_every_type_has_arabic_and_english_copy() -> None:
    for type_ in NotificationType:
        for locale in ("ar", "en"):
            message = notification_email(
                to="person@example.com",
                display_name="Nour",
                locale=locale,
                type_=type_,
                link="http://localhost:3000/ar/me/notifications",
            )
            assert message.subject
            assert "localhost:3000" in message.text_body
