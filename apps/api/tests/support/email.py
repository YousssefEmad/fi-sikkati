"""In-memory :class:`~app.core.email.EmailSender` used instead of SMTP in tests."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit

from app.core.email import EmailMessage

_LINK = re.compile(r"https?://\S+")


class RecordingEmailSender:
    """Captures messages so tests can read the single-use links they carry."""

    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.messages.append(message)

    def clear(self) -> None:
        self.messages.clear()

    def all_for(self, recipient: str) -> list[EmailMessage]:
        return [m for m in self.messages if m.to.lower() == recipient.lower()]

    def last_for(self, recipient: str) -> EmailMessage:
        messages = self.all_for(recipient)
        if not messages:
            msg = f"no email was sent to {recipient}; sent: {[m.to for m in self.messages]}"
            raise AssertionError(msg)
        return messages[-1]

    def token_for(self, recipient: str) -> str:
        """The ``token`` query parameter of the link in the latest email to ``recipient``."""
        message = self.last_for(recipient)
        match = _LINK.search(message.text_body)
        if match is None:
            msg = f"email {message.subject!r} contains no link"
            raise AssertionError(msg)
        tokens = parse_qs(urlsplit(match.group()).query).get("token", [])
        if not tokens:
            msg = f"link {match.group()!r} carries no token"
            raise AssertionError(msg)
        return tokens[0]
