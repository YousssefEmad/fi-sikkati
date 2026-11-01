"""Account rules (BR-ACC-*) and the module's public interface.

Other modules call these functions and receive the dataclasses declared here; the SQLAlchemy
models stay private to this module (architecture.md §3.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz.permissions import Role
from app.core.authz.ports import IdentityLoader, IdentitySnapshot
from app.core.config import Settings
from app.core.errors import ConflictError, FieldError, NotFoundError, ValidationAppError
from app.core.lifecycle import (
    CancellationStats,
    DeletionGuard,
    NoopCancellationStats,
    NoopDeletionGuard,
)
from app.modules.users.models import (
    DISPLAY_NAME_MIN_LENGTH,
    AccountStatus,
    IdentityVerificationStatus,
    User,
)
from app.modules.users.names import display_name_key
from app.modules.users.repository import UserRepository


@dataclass(frozen=True, slots=True)
class AccountView:
    """Everything the owner of an account may see about it (``GET /me``)."""

    id: UUID
    email: str
    phone: str | None
    status: AccountStatus
    email_verified: bool
    phone_verified: bool
    identity_verification_status: IdentityVerificationStatus
    roles: frozenset[Role]
    locale: str
    display_name: str
    full_name: str
    city: str | None
    bio: str | None
    date_of_birth: date
    created_at: datetime
    last_login_at: datetime | None
    deletion_requested_at: datetime | None
    photo_file_id: UUID | None
    share_phone_with_trip_peers: bool


@dataclass(frozen=True, slots=True)
class PublicProfileView:
    """What any signed-in user may see about another user (privacy: security.md §4)."""

    user_id: UUID
    display_name: str
    city: str | None
    is_driver: bool
    identity_verified: bool
    member_since: datetime
    photo_file_id: UUID | None
    cancellations_last_90_days: int


@dataclass(frozen=True, slots=True)
class CredentialRecord:
    """The minimum the auth module needs to check a password and decide what to do next."""

    user_id: UUID
    email: str
    display_name: str
    password_hash: str
    status: AccountStatus
    locale: str
    email_verified: bool
    deletion_requested_at: datetime | None


@dataclass(frozen=True, slots=True)
class RegistrationOutcome:
    """Whether a new account was created, without telling the caller's client either way."""

    created: bool
    user_id: UUID
    email: str
    display_name: str
    locale: str


def _account_view(user: User) -> AccountView:
    return AccountView(
        id=user.id,
        email=user.email,
        phone=user.phone_e164,
        status=user.status,
        email_verified=user.email_verified,
        phone_verified=user.phone_verified,
        identity_verification_status=user.identity_verification_status,
        roles=user.role_set,
        locale=user.locale,
        display_name=user.profile.display_name,
        full_name=user.profile.full_name,
        city=user.profile.city,
        bio=user.profile.bio,
        date_of_birth=user.date_of_birth,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        deletion_requested_at=user.deletion_requested_at,
        photo_file_id=user.profile.photo_file_id,
        share_phone_with_trip_peers=user.profile.share_phone_with_trip_peers,
    )


def _credential_record(user: User) -> CredentialRecord:
    return CredentialRecord(
        user_id=user.id,
        email=user.email,
        display_name=user.profile.display_name,
        password_hash=user.password_hash,
        status=user.status,
        locale=user.locale,
        email_verified=user.email_verified,
        deletion_requested_at=user.deletion_requested_at,
    )


def _display_name_taken() -> ConflictError:
    return ConflictError(
        "That display name is already used.",
        code="DISPLAY_NAME_TAKEN",
        errors=[
            FieldError(
                field="displayName",
                code="DISPLAY_NAME_TAKEN",
                message="Choose a different display name.",
            )
        ],
    )


def _is_display_name_conflict(exc: IntegrityError) -> bool:
    return "display_name_key" in str(exc.orig)


def age_in_years(date_of_birth: date, today: date) -> int:
    had_birthday = (today.month, today.day) >= (date_of_birth.month, date_of_birth.day)
    return today.year - date_of_birth.year - (0 if had_birthday else 1)


class UserService:
    """Account lifecycle: creation, profile, status and deletion."""

    def __init__(
        self,
        repository: UserRepository,
        settings: Settings,
        deletion_guard: DeletionGuard | None = None,
        cancellation_stats: CancellationStats | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._deletion_guard = deletion_guard or NoopDeletionGuard()
        self._cancellations = cancellation_stats or NoopCancellationStats()

    # --- reads ---------------------------------------------------------------------------

    async def get_account(self, user_id: UUID) -> AccountView:
        return _account_view(await self.require_user(user_id))

    async def require_user(self, user_id: UUID) -> User:
        user = await self._repository.get(user_id)
        if user is None:
            raise NotFoundError("Account not found.")
        return user

    async def grant_role(self, user_id: UUID, role: Role, *, granted_by: UUID | None) -> None:
        await self._repository.grant_role(user_id, role, granted_by=granted_by)

    async def set_photo(self, user_id: UUID, file_id: UUID) -> AccountView:
        user = await self.require_user(user_id)
        user.profile.photo_file_id = file_id
        return _account_view(user)

    async def get_credentials(self, email: str) -> CredentialRecord | None:
        user = await self._repository.get_by_email(email)
        return _credential_record(user) if user is not None else None

    async def get_credentials_by_id(self, user_id: UUID) -> CredentialRecord | None:
        user = await self._repository.get(user_id)
        return _credential_record(user) if user is not None else None

    async def get_public_profile(self, user_id: UUID) -> PublicProfileView:
        user = await self._repository.get(user_id)
        # Non-active accounts are invisible to other users: 404, not 403 — the caller has no
        # right to learn that the account exists (permission-matrix.md §3.3).
        if user is None or not user.is_active:
            raise NotFoundError("User not found.")
        days = self._settings.bookings_cancellation_window_days
        cancellations = await self._cancellations.count_recent(
            self._repository.session, user.id, days=days
        )
        return PublicProfileView(
            user_id=user.id,
            display_name=user.profile.display_name,
            city=user.profile.city,
            is_driver=Role.DRIVER in user.role_set,
            identity_verified=(
                user.identity_verification_status is IdentityVerificationStatus.APPROVED
            ),
            member_since=user.created_at,
            photo_file_id=user.profile.photo_file_id,
            cancellations_last_90_days=cancellations,
        )

    async def load_identity(self, user_id: UUID) -> IdentitySnapshot | None:
        """Authorization snapshot read fresh on every authenticated request."""
        state = await self._repository.get_status_and_verification(user_id)
        if state is None:
            return None
        status, email_verified_at, phone_verified_at = state
        return IdentitySnapshot(
            roles=await self._repository.list_roles(user_id),
            is_active=status is AccountStatus.ACTIVE,
            email_verified=email_verified_at is not None,
            phone_verified=phone_verified_at is not None,
        )

    # --- registration --------------------------------------------------------------------

    async def register(
        self,
        *,
        email: str,
        password_hash: str,
        display_name: str,
        full_name: str,
        date_of_birth: date,
        locale: str,
        phone_e164: str | None,
        accepted_terms_version: str,
        accepted_privacy_version: str,
    ) -> RegistrationOutcome:
        """Create an account (BR-ACC-01, BR-ACC-08).

        When the email is already taken the outcome says so instead of raising: the caller must
        answer identically either way (BR-AUTH-03), and only the email that is sent differs.
        """
        self._check_minimum_age(date_of_birth)
        self._check_legal_versions(accepted_terms_version, accepted_privacy_version)

        existing = await self._repository.get_by_email(email)
        if existing is not None:
            return RegistrationOutcome(
                created=False,
                user_id=existing.id,
                email=existing.email,
                display_name=existing.profile.display_name,
                locale=existing.locale,
            )

        name_key = await self._reserve_display_name(display_name)
        try:
            user = await self._repository.create(
                email=email,
                password_hash=password_hash,
                display_name=display_name,
                display_name_key=name_key,
                full_name=full_name,
                date_of_birth=date_of_birth,
                locale=locale,
                phone_e164=phone_e164,
                terms_version=accepted_terms_version,
                privacy_version=accepted_privacy_version,
                legal_accepted_at=datetime.now(UTC),
                # Every new account is a passenger; DRIVER and ADMIN are granted elsewhere
                # (BR-ACC-02, BR-ACC-03).
                roles=frozenset({Role.PASSENGER}),
            )
        except IntegrityError as exc:
            if not _is_display_name_conflict(exc):
                raise
            raise _display_name_taken() from exc
        return RegistrationOutcome(
            created=True,
            user_id=user.id,
            email=user.email,
            display_name=user.profile.display_name,
            locale=user.locale,
        )

    def _check_minimum_age(self, date_of_birth: date) -> None:
        today = datetime.now(UTC).date()
        if date_of_birth > today:
            raise ValidationAppError(
                "Date of birth cannot be in the future.",
                errors=[
                    FieldError(
                        field="dateOfBirth",
                        code="INVALID",
                        message="Date of birth cannot be in the future.",
                    )
                ],
            )
        minimum = self._settings.accounts_minimum_age_years
        if age_in_years(date_of_birth, today) < minimum:
            raise ValidationAppError(
                f"You must be at least {minimum} years old to use Fi Sikkati.",
                errors=[
                    FieldError(
                        field="dateOfBirth",
                        code="MINIMUM_AGE",
                        message=f"Minimum age is {minimum} years.",
                    )
                ],
            )

    def _check_legal_versions(self, terms_version: str, privacy_version: str) -> None:
        """BR-ACC-08: the client must accept the *current* documents, not an older copy."""
        expected = (self._settings.legal_terms_version, self._settings.legal_privacy_version)
        if (terms_version, privacy_version) != expected:
            raise ConflictError(
                "The terms of service or privacy policy have changed. Reload and try again.",
                code="LEGAL_VERSION_MISMATCH",
            )

    async def _reserve_display_name(self, display_name: str, *, user_id: UUID | None = None) -> str:
        key = display_name_key(display_name)
        if len(key) < DISPLAY_NAME_MIN_LENGTH:
            raise ValidationAppError(
                "Display name must contain at least 2 letters.",
                errors=[
                    FieldError(
                        field="displayName",
                        code="LENGTH",
                        message="Display name must contain at least 2 letters.",
                    )
                ],
            )
        owner = await self._repository.get_by_display_name_key(key)
        if owner is not None and owner.id != user_id:
            raise _display_name_taken()
        return key

    # --- mutations -----------------------------------------------------------------------

    async def update_profile(
        self,
        user_id: UUID,
        *,
        display_name: str | None = None,
        full_name: str | None = None,
        city: str | None = None,
        bio: str | None = None,
        locale: str | None = None,
        phone_e164: str | None = None,
        clear_phone: bool = False,
        share_phone_with_trip_peers: bool | None = None,
    ) -> AccountView:
        user = await self._repository.get(user_id)
        if user is None:
            raise NotFoundError("Account not found.")
        if display_name is not None:
            user.profile.display_name = display_name
            user.profile.display_name_key = await self._reserve_display_name(
                display_name, user_id=user.id
            )
            try:
                await self._repository.session.flush()
            except IntegrityError as exc:
                if not _is_display_name_conflict(exc):
                    raise
                raise _display_name_taken() from exc
        if full_name is not None:
            user.profile.full_name = full_name
        if city is not None:
            user.profile.city = city or None
        if bio is not None:
            user.profile.bio = bio or None
        if locale is not None:
            user.locale = locale
        if clear_phone:
            user.phone_e164 = None
        elif phone_e164 is not None:
            await self._set_phone(user, phone_e164)
        if share_phone_with_trip_peers is not None:
            user.profile.share_phone_with_trip_peers = share_phone_with_trip_peers
        return _account_view(user)

    async def _set_phone(self, user: User, phone_e164: str) -> None:
        if phone_e164 == user.phone_e164:
            return
        owner = await self._repository.get_by_phone(phone_e164)
        if owner is not None and owner.id != user.id:
            # Unlike registration, the caller is authenticated here, so reporting the clash is
            # not an enumeration risk (api.md §3).
            raise ConflictError("That phone number is already in use.", code="PHONE_TAKEN")
        user.phone_e164 = phone_e164
        user.phone_verified_at = None

    async def set_password_hash(self, user_id: UUID, password_hash: str) -> None:
        user = await self._repository.get(user_id)
        if user is None:
            raise NotFoundError("Account not found.")
        await self._repository.set_password_hash(user, password_hash)

    async def assert_phone_available(self, user_id: UUID, phone_e164: str) -> None:
        owner = await self._repository.get_by_phone(phone_e164)
        if owner is not None and owner.id != user_id:
            raise ConflictError("That phone number is already in use.", code="PHONE_TAKEN")

    async def assign_verified_phone(
        self, user_id: UUID, phone_e164: str, verified_at: datetime
    ) -> None:
        user = await self._repository.get(user_id)
        if user is None:
            raise NotFoundError("Account not found.")
        if phone_e164 != user.phone_e164:
            await self._set_phone(user, phone_e164)
        await self._repository.mark_phone_verified(user, phone_e164, verified_at)

    async def mark_email_verified(self, user_id: UUID) -> None:
        user = await self._repository.get(user_id)
        if user is None:
            raise NotFoundError("Account not found.")
        if not user.email_verified:
            await self._repository.mark_email_verified(user, datetime.now(UTC))

    async def record_login(self, user_id: UUID) -> None:
        user = await self._repository.get(user_id)
        if user is not None:
            await self._repository.record_login(user, datetime.now(UTC))

    async def request_deletion(self, user_id: UUID) -> datetime:
        """BR-ACC-07: mark the account deleted and start the grace period.

        The rule also blocks deletion while the user has active trips (Phase 4) or accepted
        join requests (Phase 6).
        """
        user = await self._repository.get(user_id)
        if user is None:
            raise NotFoundError("Account not found.")
        blockers = await self._deletion_guard.blockers(self._repository.session, user_id)
        if blockers:
            raise ConflictError(
                "Close or finish active trips before deleting this account.",
                code="DELETE_BLOCKED",
            )
        now = datetime.now(UTC)
        user.status = AccountStatus.DELETED
        user.deletion_requested_at = now
        user.deleted_at = now
        return now + timedelta(days=self._settings.accounts_deletion_grace_days)

    async def restore_if_within_grace(self, user_id: UUID) -> bool:
        """BR-ACC-07: signing in during the grace period cancels the deletion."""
        user = await self._repository.get(user_id)
        if user is None or user.status is not AccountStatus.DELETED:
            return False
        requested_at = user.deletion_requested_at
        if user.anonymised_at is not None or requested_at is None:
            return False
        grace = timedelta(days=self._settings.accounts_deletion_grace_days)
        if datetime.now(UTC) - requested_at > grace:
            return False
        user.status = AccountStatus.ACTIVE
        user.deletion_requested_at = None
        user.deleted_at = None
        return True


def make_identity_loader(settings: Settings) -> IdentityLoader:
    """Build the :class:`~app.core.authz.ports.IdentityLoader` that ``app.main`` binds."""

    async def load(db: AsyncSession, user_id: UUID) -> IdentitySnapshot | None:
        return await UserService(UserRepository(db), settings).load_identity(user_id)

    return load
