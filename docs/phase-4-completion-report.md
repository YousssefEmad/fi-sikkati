# Phase 4 completion report — Trips

Date: 2026-10-02

## Scope delivered

Drivers with a verified email and an `ACTIVE` + `APPROVED` vehicle can create a draft trip, preview
a server-computed route, see the suggested contribution, publish, start (from 30 minutes before
departure), complete, cancel, and edit notes. Geometry is never accepted from the client
(`BR-TRIP-05`). The suggested price is computed on the server at create and recomputed at publish
(`BR-TRIP-09`, OD-007). Non-owners see jittered area points (`OD-001`, 500 m). A worker expires
unpublished drafts after departure + 60 minutes and auto-completes in-progress trips after
estimated arrival + 6 hours (`OD-017`).

Maps: `MapProvider` with `FakeMapProvider` when `MAPBOX_ACCESS_TOKEN` is unset, and Mapbox Search +
Directions when it is set (`OD-005`). The web UI draws an SVG route sketch — no Mapbox GL.

Approved open decisions consumed: OD-001, OD-005, OD-006 (corridor stored at publish), OD-007,
OD-012, OD-017, OD-023. Product-owner go-ahead 2026-10-02: recommended options treated as approved.

## Explicitly not in this phase

| Item | Why |
| --- | --- |
| Passenger search / route matching | Phase 5. Corridor, stop radius and time window are stored now so matching can use them |
| Join requests and seat reservation | Phase 6. `GET /me/trips?role=passenger` returns an empty list until then |
| In-app notifications | Phase 7 |
| Full admin trip console | Phase 9. An admin who is not the driver can cancel via `POST /trips/{id}/cancel` |
| Unauthenticated trip detail | OD-029 still OPEN; `GET /trips/{id}` requires a session |
| Live Mapbox map in the browser | OD-005: server-side Mapbox only; the web uses an SVG sketch |
| Driver price override / in-app payments | OD-007: suggested contribution, cash off-platform |

## Quality gate

Recorded in `docs/project-status.md` §Phase 4 gate. Automated checks: ruff, mypy, import-linter,
pytest (maps/pricing/trips/authz), Alembic `0004`, OpenAPI export, `pnpm typecheck` / lint / Vitest.
Playwright trip journeys are deferred to the combined product-owner test pass.

## How to try it locally

1. Infrastructure: `pnpm infra:up` (Postgres, Redis, MinIO, Mailpit).
2. API: `cd apps/api && python -m uv run alembic upgrade head && python -m uv run uvicorn app.main:create_app --factory --reload --port 8000`
3. Web: `pnpm dev` → http://localhost:3000/ar
4. Complete Phase 3 first: identity + driver application + admin approval, with an approved vehicle.
5. Account → **رحلاتي / My trips** → **انشر رحلة / Publish a trip**. Search El Obour / Nasr City
   (FakeMapProvider works without a Mapbox token), preview, save draft, publish.
6. Trip detail: publish / start / complete / cancel. Exact coordinates are shown only to the driver.
