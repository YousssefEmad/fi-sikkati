# Architecture

Fi Sikkati is a **modular monolith**: one FastAPI backend organised by domain module, one Next.js
web application organised by feature, PostgreSQL/PostGIS as the single source of truth, Redis
for cache/rate-limits/jobs/pub-sub, S3-compatible object storage for files.
Services can be extracted later along module boundaries if scale demands it (ADR-0001).

```
                     ┌──────────────────────────────┐
   Browser / PWA ───▶│  apps/web  (Next.js, SSR)     │
   (AR / EN)         └──────────────┬───────────────┘
                                    │ HTTPS  /api/v1  + WSS /ws
                                    ▼
                     ┌──────────────────────────────┐        ┌──────────────┐
                     │  apps/api  (FastAPI)          │◀──────▶│ Redis        │
                     │  modular monolith             │        │ cache/ratelim│
                     │  ─ HTTP routers               │        │ jobs/pubsub  │
                     │  ─ WebSocket gateway          │        └──────┬───────┘
                     │  ─ worker process (same code) │               │
                     └───────┬───────────────┬───────┘               │
                             │               │                       │
                             ▼               ▼                       ▼
                   ┌──────────────┐  ┌────────────────┐    ┌──────────────────┐
                   │ PostgreSQL   │  │ S3-compatible  │    │ External providers│
                   │ + PostGIS    │  │ object storage │    │ maps · email · AI │
                   └──────────────┘  └────────────────┘    └──────────────────┘
```

---

## 1. Principles applied

| Principle | How it shows up |
| --- | --- |
| Separation of concerns | router → service → repository per module; no SQL in routers, no HTTP in services |
| Explicit domain boundaries | modules talk through service interfaces or domain events, never through each other's tables |
| Backend is the source of truth | every rule in `business-rules.md` lives in `apps/api`; the frontend never re-implements rules |
| Secure by default | auth + permission dependency on every router; deny-by-default |
| Transaction safety | one unit-of-work per request; critical paths use row locks + DB constraints |
| Idempotency | `Idempotency-Key` on critical mutations; idempotent background jobs |
| Observability | request id on every log line; structured JSON; health endpoints; error tracker |
| No premature complexity | one repo, one API process type (+ worker), no microservices, no broker, no Elasticsearch |

---

## 2. Domain model

### 2.1 Bounded contexts and modules

| Module (`apps/api/app/modules/…`) | Responsibility | Owns tables |
| --- | --- | --- |
| `auth` | registration, login, sessions, refresh rotation, password reset | `auth_sessions`, `password_reset_tokens`, `email_verification_tokens` |
| `users` | user account, profile, roles, blocks, account status | `users`, `user_profiles`, `user_roles`, `user_blocks` |
| `verification` | identity + driver verification workflows, documents | `identity_documents`, `driver_verifications`, `vehicle_documents` (with `vehicles` module) |
| `vehicles` | vehicle registry | `vehicles` |
| `trips` | trip lifecycle, stops, route, price snapshot | `trips`, `trip_routes`, `trip_stops` |
| `search` | search & matching queries (read-only over `trips`) | — (queries only) |
| `bookings` | join requests, seat reservation, cancellation records | `trip_join_requests` |
| `chat` | conversations, membership, messages | `conversations`, `conversation_members`, `messages` |
| `notifications` | notification fan-out, preferences, channels | `notifications`, `notification_preferences` |
| `ratings` | ratings, aggregates | `ratings` |
| `safety` | reports, moderation actions | `reports`, `moderation_actions` |
| `pricing` | pricing rules, price computation | `pricing_rules` |
| `admin` | admin-only orchestration/read models over other modules | — |
| `audit` | append-only audit log | `audit_logs` |
| `files` | object-storage abstraction, signed URLs, upload validation | `stored_files` |
| `maps` | mapping provider abstraction (geocode, autocomplete, route) | — |
| `ai` | assistant, tool registry, output validation | `ai_interactions` |
| `platform` | feature flags, runtime settings, analytics events | `feature_flags`, `app_settings`, `analytics_events` |

Full column-level definitions are in `database.md`.

### 2.2 Aggregates and invariants

| Aggregate root | Contains | Key invariants (BR refs) |
| --- | --- | --- |
| `User` | profile, roles, status | BR-ACC-01..06 |
| `DriverVerification` | documents, decision | BR-VER-01..04 |
| `Vehicle` | documents, verification status | FR-DRV-03/04/06 |
| `Trip` | route, stops, seat counters, status, price snapshot | BR-TRIP-01..10; seat invariant BR-TRIP-03 |
| `JoinRequest` | status, seats, pickup/drop-off | BR-JOIN-01..11; only mutated inside a `Trip` row lock when seats change |
| `Conversation` | members, messages | BR-CHAT-01..06 |
| `Report` | moderation actions | BR-SAFE-01..03 |
| `PricingRule` | versioned parameters | BR-PRICE-02 |

Seat consistency (BR-JOIN-06) is the one place two aggregates (`Trip`, `JoinRequest`) change in
one transaction; it is implemented in `bookings.service.SeatAllocationService` and is the
only code path allowed to write `trips.available_seats`.

### 2.3 Domain events (in-process, post-commit)

Modules communicate side effects through a small in-process event bus that dispatches **after
the transaction commits** (to avoid notifying about rolled-back changes):

`UserRegistered`, `VerificationDecided`, `DriverRoleGranted`, `TripPublished`, `TripUpdated`,
`TripCancelled`, `TripStarted`, `TripCompleted`, `TripExpired`, `JoinRequestCreated`,
`JoinRequestAccepted`, `JoinRequestRejected`, `JoinRequestCancelled`, `JoinRequestExpired`,
`MessageSent`, `ReportCreated`, `ReportResolved`, `UserSuspended`.

Subscribers: `notifications` (creates notifications + enqueues delivery), `chat` (system
messages), `audit` (for events marked auditable), `platform.analytics`. Handlers that need
durability enqueue a job (Redis/arq) rather than doing slow work inline. There is **no external
message broker** (MEP §99).

---

## 3. Backend architecture (`apps/api`)

### 3.1 Layout

```
apps/api/
  pyproject.toml            # uv-managed; ruff, mypy (strict), pytest config
  alembic.ini
  alembic/                  # migrations (one per schema change, reversible)
  app/
    main.py                 # app factory, router registration, middleware
    core/
      config.py             # pydantic-settings; typed settings, no scattered constants
      database.py           # async engine, session factory, unit-of-work
      security.py           # password hashing (argon2id), token signing
      authz/                # roles, permissions, require_permission()
      errors.py             # AppError hierarchy → problem+json handler
      logging.py            # structlog JSON, request-id binding, PII scrubbing
      middleware.py         # request id, security headers, timing
      pagination.py         # cursor/page helpers
      events.py             # in-process post-commit event bus
      idempotency.py        # Idempotency-Key support
      rate_limit.py         # Redis sliding-window limiter
      redis.py
      time.py               # single clock abstraction (testable)
    modules/<name>/
      router.py             # HTTP only: parse → call service → serialise
      schemas.py            # Pydantic request/response models (API contract)
      models.py             # SQLAlchemy 2.x mapped classes
      repository.py         # all SQL for this module
      service.py            # business rules (BR-*), transactions
      events.py             # domain events emitted by this module
      exceptions.py         # module error codes
      dependencies.py       # FastAPI DI wiring
      jobs.py               # arq job functions (if any)
    workers/
      main.py               # arq worker settings; registers module jobs + cron
    ws/
      gateway.py            # WebSocket endpoint, auth, subscription, Redis pub/sub bridge
  tests/
    unit/ integration/ api/ authz/ concurrency/ security/ conftest.py
```

Rules: a module imports another module **only** via its `service.py` public functions or by
subscribing to events; never its `models.py`/`repository.py`. `admin` and `search` are
read-model/orchestration modules and may read other modules' models through explicit query
functions exposed by those modules. Enforced with `import-linter` contracts in CI.

### 3.2 Request lifecycle

`Middleware (request id, security headers) → Router → Dependencies (auth, permission, rate
limit, idempotency) → Service (rules, transaction) → Repository (SQL) → commit → post-commit
events → Response (Pydantic) `. Errors raised as `AppError(code, status, message, fields)` are
rendered by one handler into the format in `api.md` §3.

### 3.3 Persistence

- SQLAlchemy 2.x async with `asyncpg`; one `AsyncSession` per request (unit of work).
- Alembic migrations, autogenerate reviewed by hand; every migration reversible where practical.
- PostGIS via `geoalchemy2`; geography columns for points, geometry for route lines, GiST indexes.
- IDs: UUID v7 generated in the application (ADR-0006).
- Timestamps: `timestamptz`, always UTC; user display timezone `Africa/Cairo` default, per-user later.

### 3.4 Background jobs

`arq` (asyncio-native, Redis-backed) runs in a separate process from the same codebase
(ADR-0007). Jobs are idempotent (keyed by entity id + version), retried with backoff, observed via
structured logs and a job-status health check. Cron jobs: expire trips, expire pending requests,
"starting soon" notifications, purge expired documents, aggregate analytics.

### 3.5 Real-time

FastAPI WebSocket endpoint `/ws` authenticated with the access token on connect. The client
subscribes to channels it is authorised for (`conversation:{id}`, `user:{id}`, `trip:{id}`);
membership is re-checked per subscription. Fan-out across API instances uses Redis Pub/Sub;
PostgreSQL remains the store — a message is first persisted, then published (ADR-0008).
Real-time is used only for: chat, trip updates, notifications, seat-availability updates
(MEP §35). Everything else is plain HTTP.

### 3.6 Files

`files` module exposes `ObjectStorage` protocol (`put`, `delete`, `presigned_get`, `presigned_put`)
with an S3 implementation (MinIO locally). Buckets: `public-media` (profile photos, served via
CDN-able URLs) and `private-documents` (never public; access only via 120 s signed URLs issued
after permission + audit). Upload validation: MIME sniffing, extension allow-list, size limit,
generated object keys (`<bucket>/<owner-uuid>/<uuid7>.<ext>`), no path from client.

### 3.7 Maps abstraction

`maps.MapProvider` protocol: `geocode`, `autocomplete`, `reverse_geocode`, `route(stops) →
RouteResult(geometry, distance_m, duration_s, provider_ref)`. Domain code depends only on the
protocol. Provider implementation is Mapbox (OD-005 approved); a deterministic `FakeMapProvider`
exists for tests and for local development without a token. Results are cached in Redis with
provider-terms-compliant TTLs. The frontend uses the same provider family via a `MapView`
component wrapper so the provider can be swapped in one place on each side.

### 3.8 AI module

```
modules/ai/
  router.py          POST /ai/assistant  (flag-gated, rate-limited)
  service.py         orchestrates: prompt → LLM → tool calls → validated result
  tools/             search_trips, get_trip_details, get_user_trip_history, get_help_content
  schemas.py         strict Pydantic models for every tool input/output and final answer
  provider.py        LLMProvider protocol (vendor ⛔ OD-025); FakeLLM for tests
  guardrails.py      input length, prompt-injection heuristics, output schema validation
```

Tools are thin adapters over existing **read-only** service functions and execute with the
requesting user's identity. The module has no repository of its own beyond `ai_interactions`
(logging prompts/tool calls/outcomes for audit, PII-minimised). The AI cannot create, accept,
approve, pay, or moderate (MEP §29–§30). Every AI answer that references trips carries the trip
ids so the UI renders them from the deterministic API, not from LLM text.

---

## 4. Frontend architecture (`apps/web`)

### 4.1 Layout

```
apps/web/
  src/
    app/
      [locale]/
        (public)/            landing, how-it-works, safety, faq, about, contact, terms, privacy
        (auth)/              login, register, verify, forgot-password, reset-password
        (app)/               authenticated shell (bottom nav on mobile, sidebar on desktop)
          dashboard/
          search/  trips/[id]/  my-trips/  messages/  notifications/  profile/  settings/
          drive/             driver area: dashboard, trips/new, trips, vehicles, verification
        (admin)/admin/…      admin shell + pages
      api/                   route handlers only for BFF needs (auth cookie bridge, sitemap)
      layout.tsx  not-found.tsx  error.tsx  manifest.ts  robots.ts  sitemap.ts
    features/<domain>/       auth, trips, search, bookings, chat, notifications, profile,
                             vehicles, verification, ratings, safety, admin, ai
      components/  hooks/  api.ts (typed calls)  schemas.ts (zod)  types.ts
    components/ui/           shadcn/ui primitives (accessible, RTL-aware)
    components/layout/       shells, navigation, language switch
    components/map/          MapView wrapper (provider-agnostic)
    lib/                     api client (openapi-fetch), query client, auth, format (Intl), utils
    i18n/                    next-intl config, routing, messages/ar.json, messages/en.json
    components/brand/        logo lockup and brand assets
    lib/fonts.ts             next/font registration (Cairo for ar, Plus Jakarta Sans for en)
    app/globals.css          Tailwind v4 entry + design tokens (@theme) — see design-system.md
  tests/                     vitest + testing-library component tests
```

### 4.2 Rules

- **Server Components by default**; `"use client"` only for interactivity (forms, maps, chat, realtime).
- **Server state**: TanStack Query with typed hooks per feature (`features/trips/hooks/useTrip`).
  Server Components fetch directly and hydrate queries where useful.
- **Local UI state**: React state. **Global client state**: Zustand only for the realtime socket
  connection and the current locale/direction — nothing else without an ADR (MEP §46).
- **Forms**: React Hook Form + Zod; Zod schemas mirror API contracts but never encode business
  rules beyond shape/format (the server is authoritative, errors are surfaced from the API
  `fields` array).
- **Contract**: TypeScript types + client generated from the backend OpenAPI document into
  `packages/types` (ADR-0009); no hand-written API types.
- **i18n**: `next-intl` with `[locale]` routing (`/ar`, `/en`), `dir` set on `<html>`, ICU
  messages, `Intl` for dates/numbers/currency, logical CSS properties (Tailwind `ms-/me-/ps-/pe-`).
- **Auth**: httpOnly cookies from the API domain; Next.js middleware guards `(app)`/`(admin)`
  route groups for UX; real authorisation is always on the API.
- **Realtime**: one WebSocket connection per tab managed in a provider; events invalidate or
  patch TanStack Query caches.
- **Design system**: shadcn/ui + Tailwind with project tokens derived from the brand logo
  (see `design-system.md`); mobile-first; bottom sheet and bottom navigation patterns on mobile;
  every list has an empty state component; every destructive action uses `ConfirmDialog`.
- **SEO**: metadata API, Open Graph, canonical, `sitemap.ts`, `robots.ts`, JSON-LD on public pages.
- **PWA**: `manifest.ts`, service worker for app-shell caching only (no transactional offline).

---

## 5. Cross-cutting

| Concern | Design |
| --- | --- |
| Configuration | `pydantic-settings` (API) and validated `env.ts` (web); `.env.example` for each app; secrets via environment only |
| Error handling | one error contract (`api.md` §3); frontend maps `code` → translated message; never raw 500s to users |
| Logging | `structlog` JSON with `request_id`, `user_id` (hashed in prod), `module`, `event`; scrubbing processor for tokens/passwords/documents |
| Health | `/health/live` (process), `/health/ready` (DB, Redis, storage reachability) |
| Metrics | Prometheus-style `/metrics` on an internal port (Phase 11) |
| Error tracking | Sentry-compatible SDK on API and web; vendor confirmed in Phase 11/12 |
| Rate limiting | Redis sliding window keyed by IP and/or user, per-endpoint policies in `core/rate_limit.py` |
| Feature flags | `feature_flags` table, cached in Redis, evaluated server-side; exposed to web via `/api/v1/platform/flags` for UI hints only |
| Analytics | `analytics_events` written server-side for the whitelisted event names (PRD §8); no third-party script until ⛔ OD-030 |
| Time | server UTC; one `Clock` dependency to make time-dependent rules testable |

---

## 6. Deployment overview

See `deployment.md`. Summary: containers `web`, `api`, `worker`, plus PostgreSQL/PostGIS, Redis
and MinIO for local Compose; production runs the same images behind a TLS reverse proxy with
managed/backed-up PostgreSQL and Redis and S3-compatible storage (provider ⛔ OD-026).

---

## 7. ADR index

| ADR | Title |
| --- | --- |
| ADR-0001 | Modular monolith over microservices |
| ADR-0002 | Monorepo layout and JavaScript tooling (pnpm workspaces) |
| ADR-0003 | Python 3.12 runtime, uv, ruff, mypy strict |
| ADR-0004 | Authentication: short-lived JWT access + rotating opaque refresh sessions, cookie transport for web |
| ADR-0005 | RBAC with code-defined permissions and DB-stored role assignments |
| ADR-0006 | UUID v7 primary keys |
| ADR-0007 | Background jobs with arq on Redis |
| ADR-0008 | Real-time via FastAPI WebSockets + Redis Pub/Sub, persist-then-publish |
| ADR-0009 | OpenAPI-generated TypeScript client as the frontend/backend contract |
| ADR-0010 | API error format (RFC 9457 Problem Details with `code`) and pagination strategy |
| ADR-0011 | Money as integer minor units |
| ADR-0012 | Geographic matching with PostGIS route corridors |
| ADR-0013 | Private document storage with short-lived signed URLs |
| ADR-0014 | Async SQLAlchemy 2.x with asyncpg and one unit-of-work per request |
