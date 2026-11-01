"""Request and response bodies for ``/auth`` and ``/me/sessions``.

Validation here is about *shape* (length, format, required fields). The rules live in the
service: a schema that enforced a business rule would be a second place to change it.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.core.schemas import ApiModel
from app.core.security import PASSWORD_MAX_LENGTH
from app.modules.users.phones import normalize_phone
from app.modules.users.schemas import (
    DisplayName,
    FullName,
    Locale,
    PhoneNumber,
    trimmed_name,
)

# The minimum length is a configured rule (BR-AUTH-01) checked in the service; the schema only
# guards against absurd input so a 10 MB "password" never reaches Argon2.
Password = Annotated[str, Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)]
OpaqueToken = Annotated[str, Field(min_length=20, max_length=200)]
LegalVersion = Annotated[str, Field(min_length=1, max_length=40)]


class RegisterRequest(ApiModel):
    """``POST /auth/register`` (FR-AUTH-01, BR-ACC-08)."""

    email: EmailStr
    password: Password
    display_name: DisplayName
    full_name: FullName
    date_of_birth: date
    locale: Locale = "ar"
    phone: PhoneNumber | None = None
    # The exact documents the user ticked; the server rejects stale versions (BR-ACC-08).
    accepted_terms_version: LegalVersion
    accepted_privacy_version: LegalVersion

    @field_validator("display_name", "full_name", mode="after")
    @classmethod
    def _trim(cls, value: str) -> str:
        return trimmed_name(value)

    @field_validator("phone", mode="before")
    @classmethod
    def _phone(cls, value: object) -> object:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            return normalize_phone(value)
        return value


class PhoneStartRequest(ApiModel):
    phone: str = Field(min_length=8, max_length=20)

    @field_validator("phone", mode="before")
    @classmethod
    def _phone(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_phone(value)
        return value


class PhoneStartResponse(ApiModel):
    expires_at: datetime
    dev_code: str | None = None


class PhoneConfirmRequest(ApiModel):
    code: str = Field(pattern=r"^\d{6}$")


class AcceptedResponse(ApiModel):
    """Deliberately uninformative: used where the answer must not reveal account existence."""

    status: Literal["ACCEPTED"] = "ACCEPTED"


class LoginRequest(ApiModel):
    email: EmailStr
    password: Password


class SessionResponse(ApiModel):
    """Issued credentials.

    Browsers receive the tokens as cookies and ignore the token fields; they are populated only
    for non-browser clients, which ask for them with ``X-Client-Type: api``.
    """

    session_id: UUID
    access_token_expires_at: datetime
    csrf_token: str
    access_token: str | None = None
    refresh_token: str | None = None


class RefreshRequest(ApiModel):
    """Non-browser clients send the refresh token here; browsers send the cookie instead."""

    refresh_token: OpaqueToken | None = None


class VerifyEmailRequest(ApiModel):
    token: OpaqueToken


class ResendVerificationRequest(ApiModel):
    email: EmailStr


class ForgotPasswordRequest(ApiModel):
    email: EmailStr


class ResetPasswordRequest(ApiModel):
    token: OpaqueToken
    new_password: Password


class ChangePasswordRequest(ApiModel):
    current_password: Password
    new_password: Password


class SessionSummary(ApiModel):
    """One device in ``GET /me/sessions`` (BR-AUTH-08)."""

    id: UUID
    current: bool
    device: str | None
    ip_fingerprint: str | None
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime


class SessionListResponse(ApiModel):
    items: list[SessionSummary]
