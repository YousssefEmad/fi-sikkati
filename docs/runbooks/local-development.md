# Runbook — Local development

Status: **DONE** (Phase 1, updated Phase 2). Covers starting/stopping the local stack, resetting
the database and running every quality gate locally. There is no trip seed in Phase 2: create an
account through the web UI; Mailpit captures verification and reset emails.

## Preconditions

| Tool | Version | Notes |
| --- | --- | --- |
| Node.js | 24.x | `.nvmrc` |
| pnpm | 12.x | `npm install -g pnpm` (corepack is not required) |
| Python | 3.12 (managed by uv) | The host Python version does not matter; `uv` downloads 3.12 |
| uv | ≥ 0.12 | `pip install --user uv` or the official installer; `python -m uv` also works |
| Docker + Compose v2 | any current | Docker Desktop on Windows/macOS |

## First run

```
pnpm setup            # scripts/dev-setup.mjs — idempotent
```

The script checks tooling, creates `apps/api/.env`, `apps/web/.env.local` and
`infra/compose/.env` from their `.env.example` files (never overwriting), starts the
infrastructure containers, installs Python and Node dependencies, applies migrations and
regenerates the typed API client.

Manual equivalent:

```
copy apps\api\.env.example apps\api\.env
copy apps\web\.env.example apps\web\.env.local
copy infra\compose\.env.example infra\compose\.env
pnpm infra:up
cd apps/api && uv sync && uv run alembic upgrade head && cd ../..
pnpm install && pnpm types:generate
```

### Port conflicts

The compose stack publishes PostgreSQL on `5432`, Redis on `6379`, MinIO on `9100`/`9101` and
Mailpit on `8025`/`1025` by default. If another project already uses a port, override it in
`infra/compose/.env` (see `infra/compose/.env.example`), e.g. `POSTGRES_PORT=5433`, and set the
same port in `apps/api/.env` (`DATABASE_URL`, `MIGRATION_DATABASE_URL`).

Connection URLs use `127.0.0.1`, not `localhost`: on some Windows hosts `localhost` resolves to
`[::1]` first, and Docker publishes on IPv4 only, which shows up as "connection refused".

## Start

Two terminals:

```
cd apps/api && uv run uvicorn app.main:create_app --factory --reload --port 8000
pnpm dev                         # web on http://localhost:3000
```

| URL | What |
| --- | --- |
| http://localhost:3000/ar , /en | Web app (Arabic default, English) |
| http://localhost:8000/api/v1/docs | Swagger UI (development/test/staging only) |
| http://localhost:8000/health/ready | API readiness (DB + Redis) |
| http://localhost:9101 | MinIO console (`fisikkati` / `fisikkati_dev_secret`) |
| http://localhost:8025 | Mailpit inbox (captures all outgoing email) |

Full containerised stack (API, worker, web, migrations) instead of the two terminals:

```
pnpm stack:up                    # docker compose --profile app up --build
```

## Stop / reset

```
pnpm infra:down                  # stop containers, keep data
pnpm infra:reset                 # stop and DELETE volumes (database, MinIO buckets)
```

`infra:reset` is the only way to re-run `infra/compose/postgres/init/*` (roles, databases,
extensions), because PostgreSQL init scripts run once on an empty volume.

## Quality gates (run before every commit / PR)

Backend (`apps/api`):

```
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run lint-imports
uv run pytest                         # unit + API tests (no services needed)
$env:RUN_INTEGRATION="1"; uv run pytest   # + integration tests against the compose stack
uv run alembic upgrade head && uv run alembic check
```

Frontend / workspace (repo root):

```
pnpm format
pnpm typecheck
pnpm lint
pnpm test
pnpm --filter @fi-sikkati/web build
```

E2E (API on :8000 and web on :3000 must be running):

```
pnpm --filter @fi-sikkati/e2e install-browsers   # once
pnpm e2e
```

## When the API contract changes

```
cd apps/api && uv run python scripts/export_openapi.py ../../packages/types/openapi.json
cd ../.. && pnpm types:generate
```

Commit both `packages/types/openapi.json` and `packages/types/src/schema.d.ts`; CI fails when
either drifts from the FastAPI app.

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `connection refused` to `127.0.0.1:5432` | Container not running or port overridden — `docker compose -f infra/compose/docker-compose.yml ps`; align `POSTGRES_PORT` and `apps/api/.env` |
| `permission denied to create extension "postgis"` | The migrator role cannot create extensions; run `pnpm infra:reset` so the init script installs them as superuser |
| `ERR_PNPM_IGNORED_BUILDS` | Add the dependency to `allowBuilds` in `pnpm-workspace.yaml` (only after reviewing its install script) |
| Vitest first test times out | Cold jsdom start on a slow machine; `testTimeout` is already 20 s — re-run |
| Next.js type error on `next/root-params` | Run `pnpm --filter @fi-sikkati/web exec next typegen` (the `typecheck`/`lint` scripts already do) |
