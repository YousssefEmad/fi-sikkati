# Project Status

Authoritative tracker for Fi Sikkati. Updated at the end of every phase and whenever a status changes.

Status vocabulary (used everywhere in this repository):

| Status | Meaning |
| --- | --- |
| **DONE** | Implemented, tested, documented, passed quality gate |
| **PARTIALLY DONE** | Some scope delivered; remaining scope listed explicitly |
| **MOCKED** | Exists only as a stub/fake; must not be described as implemented |
| **BLOCKED** | Cannot proceed until an open decision is approved or a dependency lands |
| **NOT IMPLEMENTED** | Not started |

## Phase tracker

| Phase | Name | Status | Gate result | Notes |
| --- | --- | --- | --- | --- |
| 0 | Discovery & Architecture | **DONE** | Passed (see §Phase 0 gate) | Documentation package delivered; 30 open decisions recorded |
| 1 | Foundation | **DONE** | Passed (see §Phase 1 gate) | Monorepo, API skeleton, web skeleton, Compose stack, CI, E2E smoke |
| 2 | Authentication & Identity | **BLOCKED** | — | Blocked on OD-004 (primary identifier), OD-002 (identity verification policy), OD-019 (email provider), OD-020 (deletion), OD-021 (age/terms), OD-013 (dual mode UI) |
| 3 | Driver & Vehicle | NOT IMPLEMENTED | — | Blocked on OD-003, OD-024, OD-009 |
| 4 | Trips | NOT IMPLEMENTED | — | Blocked on OD-005 (map provider), OD-007 (pricing semantics), OD-012, OD-023 |
| 5 | Search & Route Matching | NOT IMPLEMENTED | — | Blocked on OD-006 (matching thresholds), OD-001 (location privacy), OD-029 |
| 6 | Join Requests & Seat Management | NOT IMPLEMENTED | — | Blocked on OD-008, OD-014 |
| 7 | Chat & Notifications | NOT IMPLEMENTED | — | Blocked on OD-011, OD-015, OD-019 |
| 8 | Safety & Trust | NOT IMPLEMENTED | — | Blocked on OD-010, OD-016, OD-020 |
| 9 | Admin Platform | NOT IMPLEMENTED | — | — |
| 10 | AI Assistant | NOT IMPLEMENTED | — | Blocked on OD-025 |
| 11 | Performance & Hardening | NOT IMPLEMENTED | — | — |
| 12 | Production Release | NOT IMPLEMENTED | — | Blocked on OD-026, OD-027 |

"Blocked on" means the phase cannot be *fully completed* without that decision. Parts of a phase
that do not depend on the decision may still be implemented; the affected feature stops at the
boundary and is reported as PARTIALLY DONE.

## Phase 0 gate

Quality gate: *the architecture must be internally consistent.*

Consistency checks performed (all documents cross-referenced by identifier):

| Check | Result |
| --- | --- |
| Every role in the PRD appears in the permission matrix with identical names | Pass |
| Every entity in the domain model (architecture.md) has a table in database.md | Pass |
| Every state machine in business-rules.md matches the enum values in database.md | Pass |
| Every API resource in api.md maps to a backend module in architecture.md | Pass |
| Every backend module owns tables listed in database.md (no orphan tables) | Pass |
| Every configurable value in business-rules.md has a named configuration key | Pass |
| Every "if approved" item from the master prompt has an OD entry or is explicitly deferred | Pass |
| Every ADR is referenced from at least one design document | Pass |
| No document contains a business rule not traceable to the master prompt or an OD | Pass |

## Phase 1 gate

Quality gate: *a fresh developer can clone and run; every automated gate is green.* Verified on
2026-09-29 against the local Compose stack (PostgreSQL 16 + PostGIS 3.4 on host port 5433,
Redis 7):

| Check | Result |
| --- | --- |
| `ruff check` + `ruff format --check` (apps/api) | Pass |
| `mypy` strict (apps/api) | Pass |
| `lint-imports` (core ↛ modules; platform module isolated) | Pass |
| `pytest` — 27 tests (unit, API, integration with `RUN_INTEGRATION=1`) | Pass |
| Alembic `upgrade head → check → downgrade base → upgrade head` | Pass |
| `pnpm typecheck` (web, types, e2e) | Pass |
| `pnpm lint` (ESLint strict type-checked + jsx-a11y; 0 errors, 0 warnings) | Pass |
| `pnpm test` (Vitest — 4 tests: Button, AR/EN message parity) | Pass |
| `pnpm --filter @fi-sikkati/web build` (Next.js 16, Turbopack, standalone) | Pass |
| Playwright smoke — 18 tests (desktop + mobile, `ar` + `en`, axe WCAG 2.2 AA) | Pass |
| OpenAPI export == committed `packages/types/openapi.json`; generated client compiles | Pass |
| Manual: landing page in RTL Arabic and LTR English; API status "connected" | Pass |
| CI workflow (`.github/workflows/ci.yml`) | Authored; **not yet executed** — no GitHub remote exists |
| Docker images build (`apps/api`, `apps/web`) | **NOT VERIFIED** locally (time budget); covered by the `docker` CI job |

Known technical debt from Phase 1 (tracked here, not hidden in code):

| Item | Status | Plan |
| --- | --- | --- |
| Content-Security-Policy header | NOT IMPLEMENTED | Phase 11 hardening, after the map provider (OD-005) fixes the allowed origins |
| PWA icons | PARTIALLY DONE | Placeholder SVG icon in `manifest.webmanifest`; branded PNG + maskable icons in Phase 11 |
| Error tracking SDK (Sentry or similar) | NOT IMPLEMENTED | Vendor selection is an approval gate (MEP §96); structured logs with request ids are in place |
| Rate limiting middleware | NOT IMPLEMENTED | Arrives with authentication endpoints in Phase 2 (`RateLimitedError` already exists) |
| Development seed data | NOT IMPLEMENTED | Phase 2 (no domain tables yet) |
| Coverage thresholds in CI | NOT IMPLEMENTED | Enabled when the first domain package (auth) lands in Phase 2 |

## Feature status (product checklist)

| Capability | Status |
| --- | --- |
| Authentication | NOT IMPLEMENTED |
| Authorization (RBAC) | NOT IMPLEMENTED |
| Identity verification | NOT IMPLEMENTED |
| Driver verification | NOT IMPLEMENTED |
| Vehicle management | NOT IMPLEMENTED |
| Trip creation / editing / cancellation | NOT IMPLEMENTED |
| Trip search + geographic + time matching | NOT IMPLEMENTED |
| Seat management + concurrent booking protection | NOT IMPLEMENTED |
| Join requests | NOT IMPLEMENTED |
| Trip chat | NOT IMPLEMENTED |
| Notifications | NOT IMPLEMENTED |
| Ratings | NOT IMPLEMENTED |
| Reports / blocking / moderation | NOT IMPLEMENTED |
| Admin dashboard | NOT IMPLEMENTED |
| Audit logs | NOT IMPLEMENTED |
| Private file storage | NOT IMPLEMENTED (MinIO buckets `public-media` / `private-documents` provisioned locally; no upload code) |
| API documentation (OpenAPI) | PARTIALLY DONE — generated from code, served in non-production, exported to `packages/types`; only platform/health endpoints exist |
| Database migrations | PARTIALLY DONE — Alembic wired (async, migrator role, CI round-trip); one revision (extensions check); no domain tables yet |
| Automated tests / E2E | PARTIALLY DONE — pytest (27), Vitest (4), Playwright smoke (18) with axe; domain scenarios arrive with their phases |
| CI/CD | PARTIALLY DONE — GitHub Actions workflow authored (api, web, e2e, gitleaks, docker); not executed yet (no remote); no CD |
| Docker / local environment | DONE — Compose infrastructure stack + `app` profile; multi-stage Dockerfiles for API and web |
| Monitoring / error tracking | PARTIALLY DONE — structured JSON logs with request ids and PII scrubbing, health endpoints; no metrics or error-tracking vendor (approval gate) |
| Arabic RTL / English LTR | DONE for the shell — locale routing, `dir`/`lang`, message parity test, RTL layout, language switcher |
| SEO public pages | PARTIALLY DONE — metadata, `robots.txt`, `sitemap.xml` with hreflang alternates for the landing page only |
| PWA | PARTIALLY DONE — web manifest with placeholder icon; no service worker (none planned for transactional features) |
| AI assistant | NOT IMPLEMENTED |
| Payments | NOT IMPLEMENTED (intentionally; requires approval — OD-007) |

## Environment inspected (2026-09-29)

| Tool | Found |
| --- | --- |
| Workspace | `e:\fi-sikkati`, empty, not a git repository |
| Node.js | 24.11.1 (npm 11.6.2; pnpm not installed) |
| Python | 3.14.0 (pip 25.2; uv not installed) |
| Docker | CLI 29.7.2, Compose v5.4.0 (daemon state not confirmed) |
| Git | 2.55.0 |

Implications are recorded in ADR-0002 (repository tooling) and ADR-0003 (Python runtime).

Installed during Phase 1: pnpm 12.6.0 (`npm install -g pnpm`), uv 0.12.20 (`pip install --user
uv`, invoked as `python -m uv`), Docker Desktop started. Host ports 5432 and 9000 were occupied
by another project's containers, which is why the compose stack supports port overrides.
