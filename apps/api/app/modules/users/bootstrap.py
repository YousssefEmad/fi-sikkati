"""Grant staff roles from environment bootstrap lists (docs/runbooks/bootstrap-admin.md)."""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz.permissions import Role
from app.core.config import Settings
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

log = structlog.get_logger("app.users.bootstrap")


async def apply_bootstrap_roles_for_user(
    session: AsyncSession,
    settings: Settings,
    *,
    user_id: UUID,
    email: str,
) -> list[Role]:
    """Grant ADMIN / SUPER_ADMIN when the email is listed in bootstrap env vars."""
    normalized = email.strip().lower()
    wanted: list[Role] = []
    if normalized in settings.bootstrap_super_admin_emails:
        wanted.append(Role.SUPER_ADMIN)
    if normalized in settings.bootstrap_admin_emails or Role.SUPER_ADMIN in wanted:
        wanted.append(Role.ADMIN)
    if not wanted:
        return []

    repo = UserRepository(session)
    granted: list[Role] = []
    for role in wanted:
        before = await repo.list_roles(user_id)
        await repo.grant_role(user_id, role, granted_by=None)
        after = await repo.list_roles(user_id)
        if role not in before and role in after:
            granted.append(role)
    if granted:
        log.info(
            "bootstrap_roles_granted",
            user_id=str(user_id),
            email=normalized,
            roles=[role.value for role in granted],
        )
    return granted


async def sync_bootstrap_roles(session: AsyncSession, settings: Settings) -> int:
    """Apply bootstrap roles to every matching existing account (startup)."""
    emails = settings.bootstrap_admin_emails | settings.bootstrap_super_admin_emails
    if not emails:
        return 0
    result = await session.execute(select(User).where(User.email.in_(emails)))
    count = 0
    for user in result.scalars():
        granted = await apply_bootstrap_roles_for_user(
            session, settings, user_id=user.id, email=user.email
        )
        count += len(granted)
    return count
