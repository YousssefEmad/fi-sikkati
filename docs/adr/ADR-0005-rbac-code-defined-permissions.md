# ADR-0005 — RBAC with code-defined permissions and DB-stored role assignments

**Status**: Accepted · **Date**: 2026-09-29

## Context

MEP §27 requires explicit permissions and a maintained permission matrix. §42 lists
`roles`, `permissions`, `user_roles` as *potential* entities. Only three roles exist and future
roles are not approved.

## Decision

Roles and permissions are enums/constants in `app/core/authz/`. The role→permission mapping is a
single reviewed Python module that mirrors `permission-matrix.md`. Only **role assignments**
(`user_roles`) live in the database. Ownership/membership checks are in services.

## Alternatives

- DB tables for roles and permissions with an admin UI: allows privilege changes without code
  review and without tests; drift from the documented matrix; unnecessary for 3 roles.
- ABAC/policy engine (OPA, Casbin): overkill.

## Consequences

- Adding a role/permission is a code change with tests and matrix update.
- The authz test suite can enumerate the mapping exhaustively.
- If future roles need per-community scoping (OD-028), a `scope` column on `user_roles` is the
  extension point.
