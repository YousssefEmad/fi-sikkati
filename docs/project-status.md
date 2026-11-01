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
| 2 | Authentication & Identity | **DONE** | Passed (see §Phase 2 gate) | Accounts, sessions, email verify, reset, profile, close account. Identity *document upload* is Phase 3 |
| 3 | Driver & Vehicle | **DONE** | Passed (see §Phase 3 gate) | Identity docs, driver apply, vehicles, admin queue, private files. Licence-expiry reminder cron is Phase 7 |
| 4 | Trips | **DONE** | Passed (see §Phase 4 gate) | Create/edit/publish/start/complete/cancel; FakeMapProvider + optional Mapbox; suggested contribution |
| 5 | Search & Route Matching | **DONE** | Passed (see §Phase 5 gate) | `GET /search/trips` PostGIS corridor + direction; EXACT vs ON_ROUTE; login required (OD-029). Join is Phase 6 |
| 6 | Join Requests & Seat Management | **DONE** | Passed (see §Phase 6 gate) | Atomic seat lock; OD-008/014 approved 2026-10-15. Reminder notifications are Phase 7 |
| 7 | Chat & Notifications | **DONE** | Passed (2026-10-19) | Trip chat + in-app/email notifications. Community chat deferred (OD-015). |
| 8 | Safety & Trust | **DONE** | Passed (2026-10-19) | Ratings, reports, blocks; search/join hide blocked drivers |
| 9 | Admin Platform | **DONE** | Passed (2026-10-19) | ADMIN (community ops) vs SUPER_ADMIN (platform owner only) |
| 10 | AI Assistant | **DONE** | Passed (2026-10-19) | Flag-gated rules provider; never books |
| 11 | Performance & Hardening | **DONE** | Passed (2026-10-19) | CSP, HSTS, admin rate limits, readiness already in place |
| 12 | Production Release | **PARTIALLY DONE** | — | PWA installable; prod compose + Caddy authored. Hosting/domain still OD-026/027 |

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
| Playwright smoke — 18 tests (desktop + mobile, `ar` + `en`, axe WCAG 2.2 AA) | Pass (re-verified after the brand redesign) |
| OpenAPI export == committed `packages/types/openapi.json`; generated client compiles | Pass |
| Manual: landing page in RTL Arabic and LTR English, desktop + mobile; API status "connected" | Pass |
| CI workflow (`.github/workflows/ci.yml`) | Authored; **not yet executed** — no GitHub remote exists |
| Docker images build (`apps/api`, `apps/web`) | **NOT VERIFIED** locally (time budget); covered by the `docker` CI job |

## Phase 2 gate

Quality gate: *a user can create an account, confirm email, sign in, manage the profile and
sessions, and close the account; identity document upload is out of scope.* Verified 2026-10-02.

| Check | Result |
| --- | --- |
| Approved ODs for this phase recorded (002, 004, 013, 019, 020, 021) | Pass |
| `ruff check` + `ruff format --check` (apps/api) | Pass |
| `mypy` strict | Pass |
| `lint-imports` | Pass |
| `pytest` including auth/users/audit (unit, API, integration, authz, security) | Pass |
| Alembic round-trip on identity schema | Pass |
| OpenAPI export == `packages/types/openapi.json`; `pnpm types:generate` is current | Pass |
| `pnpm typecheck` / `pnpm lint` / Vitest (messages, Field, auth helpers) | Pass |
| Playwright Phase 1 smoke + Phase 2 auth (register/sign-in/me/sign-out, axe on auth screens) | Pass |
| Manual: register in the browser, Mailpit link, sign-in, account pages | Pass |

## Phase 3 gate

Quality gate: *a user can upload identity documents, apply to drive with a vehicle, and an
admin can review both queues; private files are never public and are purged after 30 days.*
Verified 2026-10-02.

| Check | Result |
| --- | --- |
| Approved ODs for this phase recorded (003, 009, 022, 024) | Pass |
| `ruff check` + `ruff format --check` (apps/api) | Pass |
| `mypy` strict | Pass |
| `lint-imports` (verification > vehicles > auth > users > files > platform) | Pass |
| `pytest` including files validation, verification/vehicle API, authz matrix | Pass |
| Alembic `0003` applied; `alembic check` clean | Pass |
| OpenAPI export == `packages/types/openapi.json`; `pnpm types:generate` is current | Pass |
| `pnpm typecheck` / `pnpm lint` / Vitest (11 tests; message parity includes Verification/Drive/Vehicles/Admin) | Pass |
| Playwright identity/driver journeys (testing.md §3 scenarios 3–4) | Deferred — product-owner combined test pass |
| Manual browser walkthrough of `/me/verification`, `/drive`, `/admin/verifications` | Deferred with the same test pass |

Known remaining items from this phase (not hidden):

| Item | Status | Plan |
| --- | --- | --- |
| Licence-expiry reminder email | NOT IMPLEMENTED | Phase 7 — date + `verification.licence_expiry_notice_days` are stored now |
| Full admin console | NOT IMPLEMENTED | Phase 9 |
| In-app notifications | NOT IMPLEMENTED | Phase 7; review outcomes are emailed |
| Antivirus / ClamAV scan | NOT IMPLEMENTED | `SCAN_UNAVAILABLE`; magic-byte + re-encode + PDF script reject |
| Phone OTP | NOT IMPLEMENTED | Separate SMS vendor approval (OD-004) |
| User blocking | NOT IMPLEMENTED | Phase 8 |
| Coverage `%` fail-under in CI | PARTIALLY DONE | Auth/users/verification tests exist; numeric threshold still informative until the report is wired |

Phase 2 leftovers closed in this phase: identity document upload + admin review; profile photo.

## Phase 4 gate

Quality gate: *an approved driver can create, publish, start, complete and cancel a trip; the
route and suggested contribution are computed on the server; non-owners never see exact pickup
coordinates.* Verified 2026-10-02.

| Check | Result |
| --- | --- |
| Approved ODs for this phase recorded (001, 005, 006 corridor, 007, 012, 017, 023) | Pass |
| `ruff check` + `ruff format --check` (apps/api) | Pass |
| `mypy` strict | Pass |
| `lint-imports` (trips > maps > pricing > verification > vehicles > auth > users > files > platform) | Pass |
| `pytest` including maps/pricing/trips API and authz matrix | Pass (227 tests, `RUN_INTEGRATION=1`) |
| Alembic `0004` applied; `alembic check` clean | Pass |
| OpenAPI export == `packages/types/openapi.json`; `pnpm types:generate` is current | Pass |
| `pnpm typecheck` / `pnpm lint` / Vitest (message parity includes Trips) | Pass |
| Playwright trip journeys | Deferred — product-owner combined test pass |
| Manual browser walkthrough of `/trips/new`, `/me/trips`, `/trips/{id}` | Deferred with the same test pass |

Known remaining items (not hidden):

| Item | Status | Plan |
| --- | --- | --- |
| Passenger search | DONE | Phase 5 |
| Join requests | DONE | Phase 6 |
| Mapbox GL in the browser | NOT IMPLEMENTED | Not in MVP; SVG sketch is the UI |
| Unauthenticated trip visibility | DONE | OD-029 approved 2026-10-02: session required |

Phase 3 leftovers closed in this phase: attaching an approved vehicle to a published trip
(`FR-DRV-06`).

## Phase 5 gate

Quality gate: *a signed-in passenger can search published trips by pickup, drop-off, date and
time; results are geographically compatible and privacy-filtered; anonymous callers are
rejected.* Verified 2026-10-02.

| Check | Result |
| --- | --- |
| Approved ODs for this phase recorded (001, 006, 029) | Pass |
| `ruff check` + `ruff format --check` (apps/api) | Pass |
| `mypy` strict | Pass |
| `lint-imports` (search > trips > maps > pricing > verification > vehicles > auth > users > files > platform) | Pass |
| `pytest` including search window, search API, platform config, authz matrix | Pass (239 tests, `RUN_INTEGRATION=1`) |
| No new Alembic revision (matching uses Phase 4 geometry) | Pass |
| OpenAPI export == `packages/types/openapi.json`; `pnpm types:generate` is current | Pass |
| `pnpm typecheck` / ESLint on search UI / Vitest (message parity includes Search) | Pass |
| Playwright search journeys | Deferred — product-owner combined test pass |
| Manual browser walkthrough of `/search` | Deferred with the same test pass |

Known remaining items (not hidden):

| Item | Status | Plan |
| --- | --- | --- |
| Join requests | DONE | Phase 6 |
| `minRating` filter | NOT IMPLEMENTED | Phase 8 — any value yields empty results |
| Block exclusion in search | NOT IMPLEMENTED | Phase 8 — `BR-MATCH-07` is a no-op |
| Mapbox GL in the browser | NOT IMPLEMENTED | Not in MVP; SVG sketch is the UI |

Phase 4 leftovers closed in this phase: passenger search and OD-029 (session required).

## Phase 6 gate

Quality gate: *a verified passenger can request a seat, the driver can accept or reject, and
concurrent accepts cannot overbook.* Verified 2026-10-15.

| Check | Result |
| --- | --- |
| OD-008 and OD-014 recorded as approved (record cancellations; expire at departure) | Pass |
| `ruff check` + `ruff format --check` (apps/api) | Pass |
| `mypy` strict on the booking, trip, and user changes | Pass |
| `lint-imports` (bookings > search > trips > …) | Pass |
| Alembic `0005` matches the models (`alembic check`) | Pass |
| `pytest` including join API, concurrency (1 seat / 10 accepts on 3 seats / parallel idempotency key), authz matrix, public profile | Pass (262 tests, `RUN_INTEGRATION=1`) |
| OpenAPI export and `pnpm types:generate` | Pass |
| `pnpm typecheck` and ESLint on the booking UI; Vitest message parity | Pass |
| Manual browser walkthrough: request a seat, accept, seat count, `/me/requests`, passenger trip list | Pass |
| Playwright join journeys | Deferred — product-owner combined test pass |

Known remaining items (not hidden):

| Item | Status | Plan |
| --- | --- | --- |
| Request notifications and the 24 h / 2 h unanswered reminders | NOT IMPLEMENTED | Phase 7. Expiry itself runs in the worker |
| Trip chat membership on accept | NOT IMPLEMENTED | Phase 7 |
| Block exclusion on create (`BR-JOIN-01`) | NOT IMPLEMENTED | Phase 8 — no `user_blocks` table, so the check is a no-op |
| `minRating` filter and search block exclusion | NOT IMPLEMENTED | Phase 8 |

Known technical debt from Phase 1 (tracked here, not hidden in code):

| Item | Status | Plan |
| --- | --- | --- |
| Content-Security-Policy header | NOT IMPLEMENTED | Phase 11 hardening, after Mapbox origins are listed from OD-005 |
| Brand illustrations / map styling | NOT IMPLEMENTED | Phase 11; icon set and palette are final, illustration work waits |
| Error tracking SDK (Sentry or similar) | NOT IMPLEMENTED | Vendor selection is an approval gate (MEP §96); structured logs with request ids are in place |
| Rate limiting middleware | DONE | Auth endpoints enforce per-IP / per-identifier limits (security.md §7) |
| Development seed data | PARTIALLY DONE | Register through the UI; FakeMapProvider has El Obour/Cairo places; no trip seed |
| Coverage thresholds in CI | PARTIALLY DONE | Domain tests exist; `--cov-fail-under` not yet a CI gate |

## Feature status (product checklist)

| Capability | Status |
| --- | --- |
| Authentication | DONE — email + password, cookie sessions, verify/reset/change, rate limits |
| Authorization (RBAC) | PARTIALLY DONE — code-defined roles/permissions; `PASSENGER` at registration; `DRIVER` on admin approval; `ADMIN` via SQL runbook; remaining admin routes in Phase 9 |
| Identity verification | DONE — upload, submit, admin review, badge status, 30-day purge |
| Driver verification | DONE — licence + vehicle, admin grant `DRIVER`, review email |
| Vehicle management | DONE — up to 3 vehicles, required registration docs, admin review |
| Trip creation / editing / cancellation | DONE — draft, publish, start, complete, cancel; privacy-filtered detail |
| Trip search + geographic + time matching | DONE — corridor + `ST_LineLocatePoint` order, EXACT/ON_ROUTE, Cairo window, cursor ranking |
| Seat management + concurrent booking protection | DONE — `SELECT … FOR UPDATE` on the trip row; `CHECK` seats; concurrency tests |
| Join requests | DONE — request, accept, reject, cancel, expire at departure, cancellation count |
| Trip chat | NOT IMPLEMENTED |
| Notifications | PARTIALLY DONE — review-outcome email; inbox/preferences are Phase 7 |
| Ratings | NOT IMPLEMENTED |
| Reports / blocking / moderation | NOT IMPLEMENTED |
| Admin dashboard | PARTIALLY DONE — verification + vehicle review queue; full console is Phase 9 |
| Audit logs | DONE for auth/account/verification/document-view events (append-only `audit_logs`) |
| Private file storage | DONE — MinIO private + public buckets; signed GET 120s for ADMIN; nightly purge |
| API documentation (OpenAPI) | DONE for shipped routes — generated from code, exported to `packages/types` |
| Database migrations | DONE through Alembic `0005` (trip join requests) |
| Automated tests / E2E | PARTIALLY DONE — pytest maps/pricing/trips/search/join/authz, Vitest; Playwright Phase 3–6 journeys deferred to the combined test pass |
| CI/CD | PARTIALLY DONE — GitHub Actions workflow authored (api, web, e2e, gitleaks, docker); not executed yet (no remote); no CD |
| Docker / local environment | DONE — Compose infrastructure stack + `app` profile; multi-stage Dockerfiles for API and web |
| Monitoring / error tracking | PARTIALLY DONE — structured JSON logs with request ids and PII scrubbing, health endpoints; no metrics or error-tracking vendor (approval gate) |
| Arabic RTL / English LTR | DONE for the shell — locale routing, `dir`/`lang`, message parity test, RTL layout, language switcher, Cairo/Plus Jakarta typography |
| Design system | DONE for the shell — brand tokens from the logo (`#CCF618`), Button/Badge/Card/Logo primitives, documented in `design-system.md`; product components follow their phases |
| SEO public pages | PARTIALLY DONE — metadata, Open Graph/Twitter card image, `robots.txt`, `sitemap.xml` with hreflang alternates for the landing page only |
| PWA | PARTIALLY DONE — web manifest with real `any` + `maskable` icons, apple touch icon and favicon generated from the logo; no service worker (none planned for transactional features) |
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
