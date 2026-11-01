# Fi Sikkati (في سكتي)

Community ride-sharing and route-matching platform. Drivers publish trips they are already
planning to make; passengers find people already going their way and request to join.

> Status: **Phase 6 — Join Requests & Seat Management complete**.
> See [`docs/project-status.md`](docs/project-status.md) for the authoritative phase tracker.

## What this is (and is not)

Fi Sikkati is **not** a ride-hailing app. Nobody "orders a car". A driver who is already going
from El Obour to Nasr City at 08:00 publishes that trip; passengers discover it, request seats,
the driver accepts or declines, and everyone communicates inside the trip. The product turns an
informal WhatsApp-group habit into a structured, safe, searchable platform.

Initial community: El Obour City and surrounding areas, Egypt. Initial expected size: ~2,000 users.

## Repository layout

```
apps/
  web/          Next.js (App Router, TypeScript) — passenger, driver and admin web application
  api/          FastAPI (Python) — modular-monolith backend, source of truth
packages/
  types/        TypeScript types + typed client generated from the backend OpenAPI schema
  config/       Shared lint / format / TS configuration
  (shared/      created only when two workspaces need the same runtime code)
docs/           Product, architecture, security, database, API and operational documentation
docs/adr/       Architecture Decision Records
docs/runbooks/  Operational runbooks
infra/compose/  Local Docker Compose stack (PostgreSQL/PostGIS, Redis, MinIO, Mailpit, app profile)
scripts/        Developer helper scripts (dev-setup)
tests/e2e/      Cross-application end-to-end tests (Playwright)
.github/        CI workflow
```

## Documentation map

| Document | Purpose |
| --- | --- |
| [`docs/project-status.md`](docs/project-status.md) | Phase tracker, what is DONE / PARTIAL / MOCKED / BLOCKED / NOT IMPLEMENTED |
| [`docs/product-requirements.md`](docs/product-requirements.md) | PRD, personas, user journeys, screens |
| [`docs/business-rules.md`](docs/business-rules.md) | Every enforced rule, state machine and configurable value |
| [`docs/permission-matrix.md`](docs/permission-matrix.md) | Roles, permissions, server-side enforcement matrix |
| [`docs/architecture.md`](docs/architecture.md) | Domain model, backend, frontend, real-time, AI, deployment architecture |
| [`docs/design-system.md`](docs/design-system.md) | Brand assets, colour/typography tokens, UI primitives, accessibility rules |
| [`docs/database.md`](docs/database.md) | ERD, entities, constraints, indexes, migrations |
| [`docs/api.md`](docs/api.md) | API conventions, error format, pagination, endpoint map |
| [`docs/api-changelog.md`](docs/api-changelog.md) | Consumer-facing API changes per release |
| [`docs/security.md`](docs/security.md) | Security architecture and controls |
| [`docs/testing.md`](docs/testing.md) | Testing strategy and quality gates |
| [`docs/deployment.md`](docs/deployment.md) | Environments, Docker, CI/CD, production topology |
| [`docs/risk-register.md`](docs/risk-register.md) | Known risks and mitigations |
| [`docs/open-decisions.md`](docs/open-decisions.md) | Unresolved product/business decisions awaiting approval |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records |
| [`docs/runbooks/`](docs/runbooks/) | Operational runbooks (local development, migrations, …) |

## Running the project

Prerequisites: Node.js 24, pnpm 12 (`npm install -g pnpm`), [uv](https://docs.astral.sh/uv/)
(Python 3.12 is downloaded by uv), Docker with Compose v2.

```
pnpm setup                                    # env files, infrastructure, deps, migrations, API client
cd apps/api && uv run uvicorn app.main:create_app --factory --reload --port 8000
pnpm dev                                      # in a second terminal → http://localhost:3000/ar
```

- Swagger UI: http://localhost:8000/api/v1/docs · readiness: http://localhost:8000/health/ready
- Ports taken by another project? Override in `infra/compose/.env` (`POSTGRES_PORT=5433`, …)
  and mirror in `apps/api/.env`. URLs use `127.0.0.1` on purpose (IPv6 `localhost` pitfall).
- Full details, quality-gate commands and troubleshooting:
  [`docs/runbooks/local-development.md`](docs/runbooks/local-development.md).

Quality gates (`pnpm format && pnpm typecheck && pnpm lint && pnpm test`, `uv run ruff/mypy/
pytest`, Alembic round-trip, Playwright `pnpm e2e`) run in CI on every PR
(`.github/workflows/ci.yml`).

## Contributing conventions

- Branches: `main`, `develop`, `feature/*`, `fix/*`, `hotfix/*`
- Commits: Conventional Commits, e.g. `feat(trips): add trip creation`, `fix(bookings): prevent seat overbooking`
- Every phase must pass: implementation → tests → lint → type check → build → security review → docs → manual verification
- Unresolved business questions are never encoded silently in code; they go to `docs/open-decisions.md`
