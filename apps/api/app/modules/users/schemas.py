"""Request and response bodies for ``/me`` and ``/users``.

The reusable field types live here because their limits come from this module's tables; the auth
module imports them so a name has one definition and one set of bounds.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.core.authz.permissions import Role
from app.core.schemas import ApiModel
from app.modules.users.models import (
    BIO_MAX_LENGTH,
    CITY_MAX_LENGTH,
    DISPLAY_NAME_MAX_LENGTH,
    DISPLAY_NAME_MIN_LENGTH,
    FULL_NAME_MAX_LENGTH,
    AccountStatus,
    IdentityVerificationStatus,
)

DisplayName = Annotated[
    str, Field(min_length=DISPLAY_NAME_MIN_LENGTH, max_length=DISPLAY_NAME_MAX_LENGTH)
]
FullName = Annotated[
    str, Field(min_length=DISPLAY_NAME_MIN_LENGTH, max_length=FULL_NAME_MAX_LENGTH)
]
City = Annotated[str, Field(max_length=CITY_MAX_LENGTH)]
Bio = Annotated[str, Field(max_length=BIO_MAX_LENGTH)]
Locale = Literal["ar", "en"]
#: E.164, the only phone format stored (BR-ACC-01: collected, never verified).
PhoneNumber = Annotated[str, Field(pattern=r"^\+[1-9][0-9]{7,14}$")]


def trimmed_name(value: str) -> str:
    trimmed = value.strip()
    if len(trimmed) < DISPLAY_NAME_MIN_LENGTH:
        msg = "must not be blank"
        raise ValueError(msg)
    return trimmed


class AccountResponse(ApiModel):
    """``GET /me`` — the owner's own account. Never returned for another user."""

    id: UUID
    email: str
    phone: str | None
    status: AccountStatus
    email_verified: bool
    phone_verified: bool
    identity_verification_status: IdentityVerificationStatus
    roles: list[Role]
    locale: str
    display_name: str
    full_name: str
    city: str | None
    bio: str | None
    date_of_birth: date
    created_at: datetime
    last_login_at: datetime | None
    deletion_requested_at: datetime | None
    photo_url: str | None
    share_phone_with_trip_peers: bool = False


class ProfileUpdateRequest(ApiModel):
    """``PATCH /me``: every field optional; omitted fields are left untouched."""

    display_name: DisplayName | None = None
    full_name: FullName | None = None
    city: City | None = None
    bio: Bio | None = None
    locale: Locale | None = None
    phone: PhoneNumber | None = None
    share_phone_with_trip_peers: bool | None = None

    @field_validator("display_name", "full_name", mode="after")
    @classmethod
    def _trim(cls, value: str | None) -> str | None:
        return trimmed_name(value) if value is not None else None


class PublicProfileResponse(ApiModel):
    """``GET /users/{userId}/public-profile`` — deliberately minimal (security.md §4).

    No email, no phone, no legal name, no exact location, no licence plate.
    """

    user_id: UUID
    display_name: str
    city: str | None
    is_driver: bool
    identity_verified: bool
    member_since: datetime
    photo_url: str | None
    cancellations_last_90_days: int


class DeleteAccountResponse(ApiModel):
    """BR-ACC-07: the account closes now and is anonymised after the grace period."""

    status: Literal["DELETED"] = "DELETED"
    anonymised_after: datetime
