# Runbook — Grant the first admin role

Status: **DONE**. Community operators (the original WhatsApp-group owners) receive `ADMIN`.
The platform owner — the developer who built the product — receives `SUPER_ADMIN` only.

`ADMIN` can review verifications, vehicles, reports, users (no contact PII), trips and
analytics. `SUPER_ADMIN` can additionally read contact PII, grant/revoke `ADMIN`/`DRIVER`,
deactivate accounts, edit settings and feature flags, and read the audit log.

`SUPER_ADMIN` cannot be granted or revoked through the HTTP API.

## Preconditions

- The account already exists (register through the web UI).
- You can run SQL as the migrator / DDL role (`MIGRATION_DATABASE_URL`).

## Steps

```
INSERT INTO user_roles (user_id, role)
SELECT u.id, 'ADMIN'
FROM users u
WHERE u.email = 'the-admin@example.com'
  AND NOT EXISTS (
    SELECT 1 FROM user_roles r
    WHERE r.user_id = u.id AND r.role = 'ADMIN'
  );
```

Community operator: use `ADMIN`. Platform owner: use `SUPER_ADMIN` instead (or as well —
the permission sets union). `PASSENGER` stays; privileges are additive (`permission-matrix.md`).

```
INSERT INTO user_roles (user_id, role)
SELECT u.id, 'SUPER_ADMIN'
FROM users u
WHERE u.email = 'the-owner@example.com'
  AND NOT EXISTS (
    SELECT 1 FROM user_roles r
    WHERE r.user_id = u.id AND r.role = 'SUPER_ADMIN'
  );
```

## Verification

`SELECT u.email, r.role FROM users u JOIN user_roles r ON r.user_id = u.id WHERE u.email = '…';`
shows both `PASSENGER` and `ADMIN`.

## Rollback

`DELETE FROM user_roles WHERE role = 'ADMIN' AND user_id = (SELECT id FROM users WHERE email = '…');`
