"""In-memory SMS sender so tests can read a confirmation code without a provider."""

from __future__ import annotations

import re

from app.core.sms import SmsMessage

_CODE = re.compile(r"\d{6}")


class RecordingSmsSender:
    def __init__(self) -> None:
        self.messages: list[SmsMessage] = []

    async def send(self, message: SmsMessage) -> None:
        self.messages.append(message)

    def code_for(self, phone: str) -> str:
        for message in reversed(self.messages):
            if message.to != phone:
                continue
            found = _CODE.search(message.body)
            if found is None:
                break
            return found.group(0)
        msg = "no confirmation code was sent to that number"
        raise AssertionError(msg)
