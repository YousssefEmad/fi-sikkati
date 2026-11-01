"""Outbound SMS for phone confirmation.

The message body is a one-time code. Neither the body nor the number is logged.
Production requires a Twilio account; local development shows the code on screen instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx
import structlog

from app.core.config import Settings

log = structlog.get_logger("app.sms")


class SmsDeliveryError(Exception):
    """The provider rejected or never accepted the message."""


@dataclass(frozen=True, slots=True)
class SmsMessage:
    to: str
    body: str


class SmsSender(Protocol):
    async def send(self, message: SmsMessage) -> None: ...


class NullSmsSender:
    """Used when no provider is configured. The caller may reveal the code in development."""

    async def send(self, message: SmsMessage) -> None:
        return None


class TwilioSmsSender:
    """Twilio Programmable SMS. Credentials stay in the environment."""

    def __init__(self, settings: Settings) -> None:
        self._sid = settings.twilio_account_sid
        self._token = settings.twilio_auth_token.get_secret_value()
        self._from = settings.sms_from

    async def send(self, message: SmsMessage) -> None:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Messages.json"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    url,
                    data={"To": message.to, "From": self._from, "Body": message.body},
                    auth=(self._sid, self._token),
                )
        except httpx.HTTPError as exc:
            log.warning("sms_failed", error=type(exc).__name__)
            raise SmsDeliveryError from exc
        if response.is_error:
            log.warning("sms_failed", status=response.status_code)
            raise SmsDeliveryError
        log.info("sms_sent")
