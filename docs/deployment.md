# Deployment Architecture

## 1. Environments (MEP §59, §84)

| Environment | Purpose | Data | Secrets |
| --- | --- | --- | --- |
| `development` | local Docker Compose | seeded synthetic | `.env` (git-ignored), from `.env.example` |
| `test` | CI and local test runs | ephemeral, created per run | CI secrets / defaults |
| `staging` | pre-production verification, E2E, manual QA | anonymised synthetic only | platform secret store |
| `production` | live | real; **never** seed data | platform secret store |

`APP_ENV` selects behaviour (docs UI on/off, cookie `Secure`, seed refusal, log format).
Configuration is environment variables validated at startup (`pydantic-settings` / `env.ts`);
the process refuses to boot with missing or invalid values.

## 2. Local development (Phase 1 deliverable)

`infra/compose/docker-compose.yml`:

| Service | Image | Notes |
| --- | --- | --- |
| `web` (profile `app`) | `apps/web` Dockerfile (dev target, hot reload) | port 3000 |
| `api` (profile `app`) | `apps/api` Dockerfile (dev target, `--reload`) | port 8000 |
| `migrate` (profile `app`) | same image as `api`, `alembic upgrade head`, runs before `api` | — |
| `worker` (profile `app`) | same image as `api`, arq entrypoint | — |
| `postgres` | `postgis/postgis:16-3.4` | `${POSTGRES_PORT:-5432}`; init scripts create roles, databases and extensions (superuser) |
| `redis` | `redis:7-alpine` | `${REDIS_PORT:-6379}` |
| `minio` + `minio-init` | `minio/minio` + `mc` job creating `public-media` (anonymous download) and `private-documents` (private) | `${MINIO_PORT:-9100}` / `${MINIO_CONSOLE_PORT:-9101}` |
| `mailpit` | fake SMTP with web UI | `${MAILPIT_UI_PORT:-8025}` / `${MAILPIT_SMTP_PORT:-1025}` |

Infrastructure services start with `docker compose up -d` (default profile); the application
containers are opt-in via `--profile app` so developers can run API/web natively with hot reload.
Host ports are overridable through `infra/compose/.env` (untracked; template in
`.env.example`) to coexist with other projects. `scripts/dev-setup.mjs` (`pnpm setup`) copies
env examples, starts infrastructure, installs dependencies, migrates and regenerates the API
client; seeding is added in Phase 2. See `docs/runbooks/local-development.md`.

PostgreSQL extensions (`postgis`, `citext`, `btree_gist`) are provisioned by a superuser, never
by the migrator role: locally via the init script, in managed environments by the platform's
extension allow-list. Migration `0001` verifies presence and fails with instructions otherwise.

## 3. Build artefacts

- `apps/api/Dockerfile`: multi-stage; `uv` resolves locked deps into a venv; runtime image
  `python:3.12-slim` with non-root user, `gdal`/`libmagic` runtime libs only; healthcheck hits
  `/health/live`. Same image runs `api` (uvicorn, multiple workers) and `worker` (arq).
- `apps/web/Dockerfile`: multi-stage; `pnpm` install with lockfile, `next build` with `output:
  'standalone'`; runtime `node:24-alpine`, non-root; healthcheck on `/`.
- Images tagged with git SHA and semantic version; SBOM generated; scanned with Trivy in CI.

## 4. CI/CD (GitHub Actions)

| Workflow | Trigger | Steps |
| --- | --- | --- |
| `ci.yml` | PR to `develop`/`main`, push | lint, typecheck, unit/integration/API tests (PostGIS + Redis services), migration up/down/up, OpenAPI drift, client generation, web build, gitleaks, pip-audit/pnpm audit |
| `e2e.yml` | PR (label or nightly) | build images → compose up → seed → Playwright → artefacts (traces, screenshots) |
| `release.yml` | tag `v*` | build + scan + push images → deploy staging → smoke → manual approval → deploy production |

Deployment steps for `api`: run migration job (`fisikkati_migrator` role) → start new
`api`/`worker` containers → health-ready → switch traffic → stop old. Rollback = redeploy the
previous image tag; migrations are written to be backward-compatible with the previous
release (expand/contract pattern) so image rollback does not require schema rollback.

## 5. Production topology (reference — provider ⛔ OD-026)

```
Internet ─▶ DNS (⛔ OD-027) ─▶ TLS reverse proxy / load balancer (Caddy or Traefik, or managed LB)
                                   ├─▶ web  (Next.js standalone, N replicas, stateless)
                                   └─▶ api  (uvicorn, N replicas, stateless)  ─▶ WebSockets sticky not required (Redis pub/sub)
                                        worker (arq, M replicas)
              PostgreSQL 16 + PostGIS (managed or single primary + streaming replica), daily base backup + WAL (PITR), 30-day retention
              Redis 7 (managed or single node; persistence not required — no source-of-truth data)
              S3-compatible object storage: buckets public-media (CDN-fronted), private-documents (private, SSE)
              SMTP/email API (⛔ OD-019), map provider (⛔ OD-005), LLM provider (⛔ OD-025)
```

Sizing for the initial 2,000-user community is small: 2× api, 1× worker, 1× web, one managed
PostgreSQL instance. Everything is stateless except PostgreSQL/Redis/storage, so horizontal
scaling is a replica count. Kubernetes is explicitly **not** required (MEP §99); a single
Docker-host or a managed container service is sufficient. The choice is OD-026.

## 6. Observability

| Aspect | Design |
| --- | --- |
| Logs | JSON to stdout → platform log collector; retention 30 days; no PII (security.md §10) |
| Health | `/health/live`, `/health/ready` (DB, Redis, storage); worker heartbeat key in Redis checked by `/health/ready?deep=1` |
| Errors | Sentry-compatible SDK (API, worker, web) with PII scrubbing; release tagging |
| Metrics (Phase 11) | Prometheus endpoint: request latency/status per route, DB pool, job queue depth, WebSocket connections |
| Alerts (Phase 12) | 5xx rate, p95 latency, readiness failures, job queue backlog, DB disk/connections, backup failure, certificate expiry |

## 7. Backups & disaster recovery (Phase 12 deliverables)

- PostgreSQL: automated daily base backups + continuous WAL archiving; PITR tested quarterly by
  restoring into staging (runbook `docs/runbooks/restore-database.md`).
- Object storage: cross-region replication for `private-documents` if the provider supports it;
  otherwise weekly sync to a second bucket; retention policy still enforced.
- Redis: not backed up (cache/queue only); jobs are idempotent and re-enqueued from DB state.
- RPO target 15 min, RTO target 2 h for the initial community (to be confirmed with OD-026).
- Rollback plan, production checklist and DR test log live in `docs/runbooks/`.

## 8. Domain, TLS, PWA

Domain ⛔ OD-027. TLS via ACME (Caddy/Traefik) or managed certificates; HSTS preload after
verification. `apps/web` serves `manifest.webmanifest`, icons and a minimal service worker for
app-shell caching only. Cookie names use the `__Host-` prefix, which requires the API to be
served on the same registrable domain as the web app (e.g. `app.<domain>` + `api.<domain>` is
**not** sufficient for `__Host-`; the reference design routes `/api/*` through the same host
via the reverse proxy).
