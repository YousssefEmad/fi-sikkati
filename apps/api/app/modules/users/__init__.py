"""User accounts, profiles and role assignments.

Owns ``users``, ``user_profiles`` and ``user_roles`` (architecture.md §2.1). Other modules reach
this data only through :mod:`app.modules.users.service`, which returns plain dataclasses — the
ORM models never leave the module.
"""
