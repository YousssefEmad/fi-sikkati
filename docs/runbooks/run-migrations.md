# Runbook — Database migrations (Alembic)

Status: **DONE** (Phase 1). Applies to every environment; production specifics are marked.

## Roles

Migrations run as `fisikkati_migrator` (schema owner) through `MIGRATION_DATABASE_URL`. The
application runs as `fisikkati_app` (DML only) and must never be able to run DDL — an
integration test asserts this (`tests/integration/test_infrastructure.py`).

PostgreSQL **extensions** (`postgis`, `citext`, `btree_gist`) are not created by migrations in
managed environments; they are provisioned once by a superuser (locally by
`infra/compose/postgres/init/grants.psql`). Revision `0001_enable_extensions` verifies they exist
and fails with an actionable message when they do not.

## Create a revision

```
cd apps/api
uv run alembic revision --autogenerate -m "add trips table"
```

Then review the generated file: autogenerate misses PostGIS index details, `CHECK` constraints
and data migrations. Name constraints through the models (naming convention in
`app/core/database.py`), never inline. Every revision must have a working `downgrade()`.

## Apply

```
uv run alembic upgrade head
uv run alembic check          # fails if models and DB schema differ
```

## Roll back

```
uv run alembic downgrade -1   # one revision
uv run alembic downgrade base # everything (development only)
```

Roll-back of a revision that dropped columns or tables loses data by design; in staging and
production, prefer a forward fix. Destructive changes follow the expand/contract pattern
(add → backfill → switch → drop in a later release) so rollbacks never need to recreate data.

## CI

`.github/workflows/ci.yml` runs `upgrade head → check → downgrade base → upgrade head` against a
fresh PostGIS container on every PR. A revision that cannot be downgraded blocks merge.

## Production (Phase 12; recorded now so the design is fixed)

1. Take/verify a backup or PITR marker.
2. Run the `migrate` job (same image as the API, `alembic upgrade head`) **before** deploying the
   new API version; migrations must be backward compatible with the previous API version.
3. Deploy the API; run smoke tests; keep the previous image available for rollback.
4. Never run `downgrade` in production without an approved incident decision.
