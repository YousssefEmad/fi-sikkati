# Phase 5 completion report — Search & Route Matching

Date: 2026-10-02

## Scope delivered

Signed-in passengers search published trips by pickup, drop-off, date and optional time.
Matching is PostGIS: both points must sit inside the stored route corridor, pickup must
precede drop-off along the line (`ST_LineLocatePoint`), and results are ranked per
`BR-MATCH-06`. Exact matches (both points within 500 m of ordered stops) are labelled
separately from on-route matches. Search results expose jittered area points, never exact
stops or plates (`OD-001`, `BR-VEH-02`).

`GET /search/trips` is rate-limited at 60 / min per user. Time windows are interpreted in
Africa/Cairo. `minRating` returns an empty list until ratings exist (Phase 8). Block
exclusion (`BR-MATCH-07`) is a no-op until Phase 8. Join is not offered — that is Phase 6.

Approved open decisions consumed: OD-001, OD-006, OD-029 (login required). Product-owner
go-ahead 2026-10-02: recommended options treated as approved.

## Explicitly not in this phase

| Item | Why |
| --- | --- |
| Join requests and seat reservation | Phase 6 |
| Ratings filter (`minRating`) | Phase 8 — any provided value yields `[]` |
| Block exclusion in ranking | Phase 8 — no `user_blocks` table |
| Unauthenticated search / trip SEO pages | OD-029: session required |
| Live Mapbox map in the browser | OD-005: server-side maps; search reuses place autocomplete |

## Quality gate

Recorded in `docs/project-status.md` §Phase 5 gate. Automated checks: ruff, mypy,
import-linter (`search` > `trips` > …), pytest 239 (search window, search API, authz),
OpenAPI export, `pnpm typecheck`, ESLint on the search UI, Vitest 11 (message parity
includes Search). Playwright search journeys are deferred to the combined product-owner
test pass.

## How to try it locally

1. Infrastructure: `pnpm infra:up` (Postgres, Redis, MinIO, Mailpit).
2. API: `cd apps/api && python -m uv run alembic upgrade head && python -m uv run uvicorn app.main:create_app --factory --reload --port 8000`
3. Web: `pnpm dev` → http://localhost:3000/ar
4. Publish a trip first (Phase 4): approved driver, El Obour → Nasr City, then **نشر**.
5. Sign in as a passenger. Landing **دوّر على رحلة / Find a ride**, or Account → search.
   Search the same places and date. FakeMapProvider works without a Mapbox token.
6. Results show match kind and a link to `/trips/{id}`. Requesting a seat is Phase 6.
