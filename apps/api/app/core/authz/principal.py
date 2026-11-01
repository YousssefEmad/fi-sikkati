"""The authenticated caller of a request."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.authz.permissions import ADMIN_ROLES, Permission, Role, permissions_for_roles


@dataclass(frozen=True, slots=True)
class Principal:
    """Who is calling, which session they are using, and what they may do.

    Built per request from the verified access token plus the current identity snapshot, so a
    role grant or revocation takes effect immediately rather than at the next token refresh.
    """

    user_id: UUID
    session_id: UUID
    roles: frozenset[Role]
    email_verified: bool
    phone_verified: bool
    # True when the credential arrived in a cookie, which is what makes CSRF checks necessary.
    cookie_authenticated: bool = False

    @property
    def permissions(self) -> frozenset[Permission]:
        return permissions_for_roles(self.roles)

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions

    def has_role(self, role: Role) -> bool:
        return role in self.roles

    @property
    def is_admin(self) -> bool:
        """ADMIN or SUPER_ADMIN: the "sees everything, filtered for nobody" read paths."""
        return bool(self.roles & ADMIN_ROLES)

    @property
    def is_super_admin(self) -> bool:
        return Role.SUPER_ADMIN in self.roles
