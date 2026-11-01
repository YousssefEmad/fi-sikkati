"""Authorization: roles, permissions as code, and the dependencies that enforce them.

`permission-matrix.md` is the specification; :mod:`app.core.authz.permissions` is its executable
form (ADR-0005). Nothing here touches the database directly: the identity behind a request is
loaded through the ports in :mod:`app.core.authz.ports`, which ``app.main`` wires to the owning
module. That keeps ``app.core`` free of imports from ``app.modules``.
"""

from app.core.authz.permissions import (
    ALL_PERMISSIONS,
    PERMISSIONS_BY_ROLE,
    Permission,
    Role,
    permissions_for_roles,
)
from app.core.authz.principal import Principal

__all__ = [
    "ALL_PERMISSIONS",
    "PERMISSIONS_BY_ROLE",
    "Permission",
    "Principal",
    "Role",
    "permissions_for_roles",
]
