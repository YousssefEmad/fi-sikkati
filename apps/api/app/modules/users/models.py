"""``users``, ``user_profiles`` and ``user_roles`` (database.md §2.1)."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Final
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.authz.permissions import Role
from app.core.database import Base, TimestampMixin, uuid_primary_key

SUPPORTED_LOCALES: Final = ("ar", "en")
DISPLAY_NAME_MIN_LENGTH: Final = 2
DISPLAY_NAME_MAX_LENGTH: Final = 60
FULL_NAME_MAX_LENGTH: Final = 120
BIO_MAX_LENGTH: Final = 300
CITY_MAX_LENGTH: Final = 80


class AccountStatus(StrEnum):
    """BR-ACC-05: only ``ACTIVE`` accounts can authenticate."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DEACTIVATED = "DEACTIVATED"
    DELETED = "DELETED"


class IdentityVerificationStatus(StrEnum):
    """BR-VER-01. Denormalised from ``identity_documents`` (created in Phase 3)."""

    NOT_SUBMITTED = "NOT_SUBMITTED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


def _pg_enum(enum: type[StrEnum], name: str) -> Enum:
    return Enum(enum, name=name, values_callable=lambda members: [m.value for m in members])


ACCOUNT_STATUS_ENUM: Final = _pg_enum(AccountStatus, "users_status_enum")
IDENTITY_VERIFICATION_STATUS_ENUM: Final = _pg_enum(
    IdentityVerificationStatus, "users_identity_verification_status_enum"
)
ROLE_ENUM: Final = _pg_enum(Role, "user_roles_role_enum")

# E.164: a leading '+', a non-zero country digit, then 7 to 14 more digits.
_E164_PATTERN: Final = r"^\+[1-9][0-9]{7,14}$"
_LOCALE_SQL_LIST: Final = ", ".join(f"'{locale}'" for locale in SUPPORTED_LOCALES)


class User(Base, TimestampMixin):
    """An account. The email address is the primary identifier (BR-ACC-01)."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(f"locale IN ({_LOCALE_SQL_LIST})", name="locale_supported"),
        CheckConstraint(
            f"phone_e164 IS NULL OR phone_e164 ~ '{_E164_PATTERN}'", name="phone_e164_format"
        ),
        Index("ix_users_status", "status"),
        Index(
            "ix_users_deletion_requested_at",
            "deletion_requested_at",
            postgresql_where=text("deletion_requested_at IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = uuid_primary_key()
    email: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True)
    phone_e164: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AccountStatus] = mapped_column(
        ACCOUNT_STATUS_ENUM,
        nullable=False,
        default=AccountStatus.ACTIVE,
        server_default=AccountStatus.ACTIVE.value,
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Set only after the SMS code for this number is confirmed.
    phone_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    identity_verification_status: Mapped[IdentityVerificationStatus] = mapped_column(
        IDENTITY_VERIFICATION_STATUS_ENUM,
        nullable=False,
        default=IdentityVerificationStatus.NOT_SUBMITTED,
        server_default=IdentityVerificationStatus.NOT_SUBMITTED.value,
    )
    # BR-ACC-08: age gate and the exact legal documents the user accepted.
    date_of_birth: Mapped[date] = mapped_column(nullable=False)
    terms_version: Mapped[str] = mapped_column(Text, nullable=False)
    privacy_version: Mapped[str] = mapped_column(Text, nullable=False)
    legal_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locale: Mapped[str] = mapped_column(Text, nullable=False, default="ar", server_default="ar")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # BR-ACC-07: deletion is a grace period, then anonymisation.
    deletion_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    anonymised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    profile: Mapped[UserProfile] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="joined", uselist=False
    )
    roles: Mapped[list[UserRole]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="UserRole.user_id",
    )

    @property
    def is_active(self) -> bool:
        return self.status is AccountStatus.ACTIVE

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None

    @property
    def phone_verified(self) -> bool:
        return self.phone_verified_at is not None

    @property
    def role_set(self) -> frozenset[Role]:
        return frozenset(assignment.role for assignment in self.roles)


class UserProfile(Base, TimestampMixin):
    """Public display data plus the private legal name."""

    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint(
            f"char_length(display_name) BETWEEN {DISPLAY_NAME_MIN_LENGTH} "
            f"AND {DISPLAY_NAME_MAX_LENGTH}",
            name="display_name_length",
        ),
        CheckConstraint(
            f"char_length(full_name) BETWEEN {DISPLAY_NAME_MIN_LENGTH} AND {FULL_NAME_MAX_LENGTH}",
            name="full_name_length",
        ),
        CheckConstraint(f"bio IS NULL OR char_length(bio) <= {BIO_MAX_LENGTH}", name="bio_length"),
        CheckConstraint(
            f"city IS NULL OR char_length(city) <= {CITY_MAX_LENGTH}", name="city_length"
        ),
        Index("user_profiles_display_name_key_key", "display_name_key", unique=True),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    display_name_key: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_file_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True
    )
    # OD-011: opt-in phone sharing with accepted trip peers. Default off.
    share_phone_with_trip_peers: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    user: Mapped[User] = relationship(back_populates="profile")


class UserRole(Base):
    """A role assignment. Roles themselves are code, not data (ADR-0005)."""

    __tablename__ = "user_roles"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[Role] = mapped_column(ROLE_ENUM, primary_key=True)
    # NULL means the system granted it (registration, driver approval).
    granted_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="roles", foreign_keys=[user_id])
