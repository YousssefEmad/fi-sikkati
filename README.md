# Fi Sikkati (في سكتي)

Community ride-sharing and route-matching platform. Drivers publish trips they are already
planning to make; passengers find people already going their way and request to join.

> Status: **Phase 0 — Discovery & Architecture** (no application code yet).
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
infra/          Docker, Compose and deployment assets
scripts/        Developer and CI helper scripts
tests/          Cross-application end-to-end tests (Playwright)
```

The `apps/`, `packages/`, `infra/`, `scripts/` and `tests/` directories are created in Phase 1.

## Documentation map

| Document | Purpose |
| --- | --- |
| [`docs/project-status.md`](docs/project-status.md) | Phase tracker, what is DONE / PARTIAL / MOCKED / BLOCKED / NOT IMPLEMENTED |
| [`docs/product-requirements.md`](docs/product-requirements.md) | PRD, personas, user journeys, screens |
| [`docs/business-rules.md`](docs/business-rules.md) | Every enforced rule, state machine and configurable value |
| [`docs/permission-matrix.md`](docs/permission-matrix.md) | Roles, permissions, server-side enforcement matrix |
| [`docs/architecture.md`](docs/architecture.md) | Domain model, backend, frontend, real-time, AI, deployment architecture |
| [`docs/database.md`](docs/database.md) | ERD, entities, constraints, indexes, migrations |
| [`docs/api.md`](docs/api.md) | API conventions, error format, pagination, endpoint map |
| [`docs/security.md`](docs/security.md) | Security architecture and controls |
| [`docs/testing.md`](docs/testing.md) | Testing strategy and quality gates |
| [`docs/deployment.md`](docs/deployment.md) | Environments, Docker, CI/CD, production topology |
| [`docs/risk-register.md`](docs/risk-register.md) | Known risks and mitigations |
| [`docs/open-decisions.md`](docs/open-decisions.md) | Unresolved product/business decisions awaiting approval |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records |

## Running the project

Local setup instructions (Docker Compose, environment variables, seeding, tests) are added in
Phase 1 — Foundation. Until then there is nothing to run.

## Contributing conventions

- Branches: `main`, `develop`, `feature/*`, `fix/*`, `hotfix/*`
- Commits: Conventional Commits, e.g. `feat(trips): add trip creation`, `fix(bookings): prevent seat overbooking`
- Every phase must pass: implementation → tests → lint → type check → build → security review → docs → manual verification
- Unresolved business questions are never encoded silently in code; they go to `docs/open-decisions.md`
