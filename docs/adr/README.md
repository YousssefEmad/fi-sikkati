# Architecture Decision Records

Format: `ADR-XXXX-title.md` with sections Context, Decision, Alternatives, Consequences, Status.
Statuses: Proposed, Accepted, Superseded (by ADR-…), Deprecated.

| ADR | Title | Status |
| --- | --- | --- |
| [ADR-0001](ADR-0001-modular-monolith.md) | Modular monolith over microservices | Accepted |
| [ADR-0002](ADR-0002-monorepo-and-js-tooling.md) | Monorepo layout and JavaScript tooling (pnpm) | Accepted |
| [ADR-0003](ADR-0003-python-runtime-and-tooling.md) | Python 3.12, uv, ruff, mypy strict | Accepted |
| [ADR-0004](ADR-0004-authentication-tokens-and-sessions.md) | JWT access + rotating refresh sessions, cookie transport for web | Accepted |
| [ADR-0005](ADR-0005-rbac-code-defined-permissions.md) | RBAC with code-defined permissions | Accepted |
| [ADR-0006](ADR-0006-uuid-v7-primary-keys.md) | UUID v7 primary keys | Accepted |
| [ADR-0007](ADR-0007-background-jobs-arq.md) | Background jobs with arq on Redis | Accepted |
| [ADR-0008](ADR-0008-realtime-websockets-redis-pubsub.md) | Real-time via WebSockets + Redis Pub/Sub | Accepted |
| [ADR-0009](ADR-0009-openapi-generated-client.md) | OpenAPI-generated TypeScript client | Accepted |
| [ADR-0010](ADR-0010-error-format-and-pagination.md) | Problem Details error format and pagination | Accepted |
| [ADR-0011](ADR-0011-money-integer-minor-units.md) | Money as integer minor units | Accepted |
| [ADR-0012](ADR-0012-postgis-route-corridor-matching.md) | PostGIS route-corridor matching | Accepted |
| [ADR-0013](ADR-0013-private-document-storage.md) | Private document storage with signed URLs | Accepted |
| [ADR-0014](ADR-0014-async-sqlalchemy-unit-of-work.md) | Async SQLAlchemy 2.x, unit-of-work per request | Accepted |

Business decisions are **not** ADRs; they live in `../open-decisions.md` until approved and then
in `../business-rules.md`.
