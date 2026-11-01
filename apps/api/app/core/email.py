"""Outbound transactional email.

OD-019 approved the *abstraction*, not a vendor: everything goes through :class:`EmailSender`,
with an SMTP implementation that talks to Mailpit in development and to whichever provider is
approved for production. Choosing that provider is still an open approval (see
`docs/open-decisions.md` OD-019).

Email bodies contain single-use links; neither the body nor the recipient is ever logged
(security.md §10).
"""

from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage
from typing import Protocol

import aiosmtplib
import structlog

from app.core.config import Settings

log = structlog.get_logger("app.email")


@dataclass(frozen=True, slots=True)
class EmailMessage:
    """One message to one recipient, in both plain text and HTML."""

    to: str
    subject: str
    text_body: str
    html_body: str


class EmailSender(Protocol):
    """Port implemented by the SMTP sender in production and a recorder in tests."""

    async def send(self, message: EmailMessage) -> None: ...


def _build_mime(message: EmailMessage, *, from_address: str, from_name: str) -> MimeMessage:
    mime = MimeMessage()
    mime["From"] = f"{from_name} <{from_address}>"
    mime["To"] = message.to
    mime["Subject"] = message.subject
    mime.set_content(message.text_body, subtype="plain", charset="utf-8")
    mime.add_alternative(message.html_body, subtype="html", charset="utf-8")
    return mime


class SmtpEmailSender:
    """Sends through any SMTP server (Mailpit locally, the approved provider in production)."""

    def __init__(self, settings: Settings) -> None:
        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._username = settings.smtp_username
        self._password = (
            settings.smtp_password.get_secret_value() if settings.smtp_password else None
        )
        self._use_tls = settings.smtp_use_tls
        self._start_tls = settings.smtp_use_starttls
        self._from_address = str(settings.email_from_address)
        self._from_name = settings.email_from_name

    async def send(self, message: EmailMessage) -> None:
        mime = _build_mime(message, from_address=self._from_address, from_name=self._from_name)
        await aiosmtplib.send(
            mime,
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            use_tls=self._use_tls,
            start_tls=self._start_tls or None,
        )
        # Subject only: the body carries single-use tokens and the address is personal data.
        log.info("email_sent", subject=message.subject)
