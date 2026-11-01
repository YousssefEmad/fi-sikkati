"""Register / verify / sign-in flows driven through the public API.

Tests use these so a change to the registration contract is fixed in one place, and so each test
reads as the scenario it is about rather than as four HTTP calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from httpx import AsyncClient, Response

from app.core.config import Settings
from app.core.security import CSRF_HEADER_NAME
from tests.support.email import RecordingEmailSender
from tests.support.sms import RecordingSmsSender

#: Long enough for the configured minimum, with no composition requirements (BR-AUTH-01).
DEFAULT_PASSWORD = "correct-horse-battery-staple"


def adult_date_of_birth(age: int = 30) -> date:
    today = datetime.now(UTC).date()
    try:
        return today.replace(year=today.year - age)
    except ValueError:  # 29 February in a year that has no 29 February
        return today.replace(year=today.year - age, month=2, day=28)


@dataclass(frozen=True, slots=True)
class Credentials:
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class Session:
    """What ``POST /auth/login`` hands back, plus the cookies now held by the client."""

    session_id: UUID
    csrf_token: str
    access_token: str | None
    refresh_token: str | None

    @property
    def csrf_headers(self) -> dict[str, str]:
        return {CSRF_HEADER_NAME: self.csrf_token}

    @property
    def bearer_headers(self) -> dict[str, str]:
        assert self.access_token is not None, "ask for tokens with X-Client-Type: api"
        return {"Authorization": f"Bearer {self.access_token}"}


class AccountFactory:
    """Drives account creation for one HTTP client."""

    def __init__(
        self,
        client: AsyncClient,
        emails: RecordingEmailSender,
        settings: Settings,
        sms: RecordingSmsSender | None = None,
    ) -> None:
        self.client = client
        self.emails = emails
        self.settings = settings
        self.sms = sms

    def payload(self, **overrides: Any) -> dict[str, Any]:
        body: dict[str, Any] = {
            "email": f"user-{uuid4().hex[:12]}@example.com",
            "password": DEFAULT_PASSWORD,
            "displayName": "راكب تجريبي",
            "fullName": "Test Passenger",
            "dateOfBirth": adult_date_of_birth().isoformat(),
            "locale": "en",
            "acceptedTermsVersion": self.settings.legal_terms_version,
            "acceptedPrivacyVersion": self.settings.legal_privacy_version,
        }
        body.update(overrides)
        return body

    async def register(self, **overrides: Any) -> tuple[Credentials, Response]:
        body = self.payload(**overrides)
        response = await self.client.post("/api/v1/auth/register", json=body)
        return Credentials(email=body["email"], password=body["password"]), response

    async def verify_email(self, email: str) -> Response:
        return await self.client.post(
            "/api/v1/auth/email/verify", json={"token": self.emails.token_for(email)}
        )

    async def login(
        self, credentials: Credentials, *, as_api_client: bool = False
    ) -> tuple[Session | None, Response]:
        headers = {"X-Client-Type": "api"} if as_api_client else {}
        response = await self.client.post(
            "/api/v1/auth/login",
            json={"email": credentials.email, "password": credentials.password},
            headers=headers,
        )
        if response.status_code != 200:
            return None, response
        session = _session_from(response.json())
        if as_api_client:
            # API clients authenticate with the body tokens; leftover cookies would hide
            # "which credential did this request actually send?" in the tests.
            self.client.cookies.clear()
        return session, response

    async def signed_in(
        self, *, as_api_client: bool = False, **overrides: Any
    ) -> tuple[Credentials, Session]:
        """Registered, email confirmed, signed in — the starting point of most tests."""
        credentials, registered = await self.register(**overrides)
        assert registered.status_code == 202, registered.text
        verified = await self.verify_email(credentials.email)
        assert verified.status_code == 204, verified.text
        session, response = await self.login(credentials, as_api_client=as_api_client)
        assert session is not None, response.text
        if self.sms is not None:
            await self.verify_phone(session)
        return credentials, session

    async def verify_phone(self, session: Session) -> str:
        """Confirm a fresh mobile number and return it in E.164."""
        assert self.sms is not None
        phone = f"+2015{uuid4().int % 100_000_000:08d}"
        started = await self.client.post(
            "/api/v1/me/phone/challenges",
            json={"phone": phone},
            headers=session.csrf_headers,
        )
        assert started.status_code == 202, started.text
        confirmed = await self.client.post(
            "/api/v1/me/phone/confirm",
            json={"code": self.sms.code_for(phone)},
            headers=session.csrf_headers,
        )
        assert confirmed.status_code == 204, confirmed.text
        return phone


def _session_from(body: dict[str, Any]) -> Session:
    return Session(
        session_id=UUID(body["sessionId"]),
        csrf_token=body["csrfToken"],
        access_token=body.get("accessToken"),
        refresh_token=body.get("refreshToken"),
    )
