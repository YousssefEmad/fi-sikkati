"""Phone alert copy stays free of names and message text."""

from app.core.config import Settings
from app.modules.notifications.emails import notification_text
from app.modules.notifications.models import NotificationType
from app.modules.notifications.push import push_configured


def test_trip_and_chat_alerts_have_both_languages() -> None:
    for kind in (
        NotificationType.JOIN_REQUEST_RECEIVED,
        NotificationType.TRIP_CANCELLED,
        NotificationType.NEW_MESSAGE,
    ):
        ar_title, ar_body = notification_text(kind, "ar")
        en_title, en_body = notification_text(kind, "en")
        assert ar_title and ar_body
        assert en_title and en_body
        assert ar_title != en_title


def test_push_is_off_without_keys() -> None:
    settings = Settings.model_validate(
        {
            "APP_ENV": "test",
            "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/db",
            "REDIS_URL": "redis://localhost:6379/0",
            "PUBLIC_WEB_URL": "http://localhost:3000",
            "AUTH_JWT_ACTIVE_KID": "test-1",
            "AUTH_JWT_PRIVATE_KEY": "dGVzdC1qd3Qtc2VlZC0zMmJ5dGVzLWxvbmcgIQ==",
            "AUTH_PASSWORD_PEPPER": "test-pepper-" + "p" * 24,
            "AUTH_CSRF_SECRET": "test-csrf-" + "c" * 24,
            "AUTH_HASH_SECRET": "test-hash-" + "h" * 24,
            "EMAIL_FROM_ADDRESS": "no-reply@fisikkati.app",
            "SMTP_HOST": "127.0.0.1",
            "VAPID_PUBLIC_KEY": "",
            "VAPID_PRIVATE_KEY": "",
        }
    )
    assert push_configured(settings) is False
