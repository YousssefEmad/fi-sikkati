"""All SQL for the users module."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz.permissions import Role
from app.core.ids import uuid7
from app.modules.users.models import (
    AccountStatus,
    IdentityVerificationStatus,
    User,
    UserProfile,
    UserRole,
)


class UserRepository:
    """Reads and writes ``users``, ``user_profiles`` and ``user_roles``.

    Never commits: the request's unit of work owns the transaction (ADR-0014).
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @property
    def session(self) -> AsyncSession:
        return self._db

    async def get(self, user_id: UUID) -> User | None:
        return await self._db.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        # ``email`` is citext, so this comparison is case-insensitive in the database.
        result = await self._db.execute(select(User).where(User.email == email))
        return result.unique().scalar_one_or_none()

    async def get_by_display_name_key(self, key: str) -> User | None:
        result = await self._db.execute(
            select(User).join(User.profile).where(UserProfile.display_name_key == key)
        )
        return result.unique().scalar_one_or_none()

    async def list_display_name_keys(self) -> list[tuple[UUID, str]]:
        """All public name keys. Fine up to a few thousand accounts."""
        result = await self._db.execute(select(UserProfile.user_id, UserProfile.display_name_key))
        return [(row.user_id, row.display_name_key) for row in result.all()]

    async def get_by_phone(self, phone_e164: str) -> User | None:
        result = await self._db.execute(select(User).where(User.phone_e164 == phone_e164))
        return result.unique().scalar_one_or_none()

    async def get_status_and_verification(
        self, user_id: UUID
    ) -> tuple[AccountStatus, datetime | None, datetime | None] | None:
        """Minimal read for authorizing a request: no profile, no joins."""
        result = await self._db.execute(
            select(User.status, User.email_verified_at, User.phone_verified_at).where(
                User.id == user_id
            )
        )
        row = result.one_or_none()
        if row is None:
            return None
        return (row.status, row.email_verified_at, row.phone_verified_at)

    async def list_roles(self, user_id: UUID) -> frozenset[Role]:
        result = await self._db.execute(select(UserRole.role).where(UserRole.user_id == user_id))
        return frozenset(result.scalars())

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        display_name: str,
        display_name_key: str,
        full_name: str,
        date_of_birth: date,
        locale: str,
        phone_e164: str | None,
        terms_version: str,
        privacy_version: str,
        legal_accepted_at: datetime,
        roles: frozenset[Role],
    ) -> User:
        user = User(
            id=uuid7(),
            email=email,
            password_hash=password_hash,
            status=AccountStatus.ACTIVE,
            identity_verification_status=IdentityVerificationStatus.NOT_SUBMITTED,
            date_of_birth=date_of_birth,
            terms_version=terms_version,
            privacy_version=privacy_version,
            legal_accepted_at=legal_accepted_at,
            locale=locale,
            phone_e164=phone_e164,
        )
        user.profile = UserProfile(
            display_name=display_name, display_name_key=display_name_key, full_name=full_name
        )
        user.roles = [UserRole(role=role) for role in sorted(roles)]
        self._db.add(user)
        await self._db.flush()
        return user

    async def set_password_hash(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        await self._db.flush()

    async def mark_email_verified(self, user: User, verified_at: datetime) -> None:
        user.email_verified_at = verified_at

    async def mark_phone_verified(self, user: User, phone_e164: str, verified_at: datetime) -> None:
        user.phone_e164 = phone_e164
        user.phone_verified_at = verified_at
        await self._db.flush()

    async def record_login(self, user: User, at: datetime) -> None:
        user.last_login_at = at
        await self._db.flush()

    async def grant_role(self, user_id: UUID, role: Role, *, granted_by: UUID | None) -> None:
        roles = await self.list_roles(user_id)
        if role in roles:
            return
        self._db.add(UserRole(user_id=user_id, role=role, granted_by=granted_by))
        await self._db.flush()
