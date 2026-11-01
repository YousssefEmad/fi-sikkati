# Phase 6 completion report — Join Requests & Seat Management

Date: 2026-10-15

## Scope delivered

A passenger with a verified email and an approved identity can request one or more seats on a
published trip. The pickup and drop-off must sit on the stored route corridor, in order
(`BR-JOIN-04`). The driver accepts or rejects. Accept locks the trip row (`SELECT … FOR UPDATE`),
decrements `available_seats`, and moves a trip with no seats left to `FULL`. Rejecting, or the
passenger cancelling an accepted request, releases those seats and returns a full trip to
`PUBLISHED`. Cancelling the trip itself does not release seats (`BR-TRIP-06`); pending and
accepted requests become `CANCELLED` with `cancelled_by` `DRIVER` or `ADMIN`. Completing a trip
marks accepted requests `COMPLETED`.

Pending requests expire at `departure_at` in the existing worker (`BR-JOIN-09`, OD-014). A
cancellation stores the actor, the time, and minutes before departure. The public profile shows
`cancellationsLast90Days` for the passenger's own cancellations plus trips they cancelled as
driver. There is no automatic warning or suspension (`BR-JOIN-10`, OD-008 option a).

Accepted passengers see exact stops (`BR-TRIP-10`) and those trips appear under
`GET /me/trips?role=passenger`. A second active request for the same trip is
`409 DUPLICATE_REQUEST`. `Idempotency-Key` is required; the same key and payload replay the
original request, a different payload is `409 IDEMPOTENCY_CONFLICT`.

Approved open decisions consumed: OD-008, OD-014. Product-owner go-ahead 2026-10-15: the
recommended options are approved.

## API

| Method | Path | Who |
| --- | --- | --- |
| POST | `/api/v1/trips/{tripId}/join-requests` | Passenger. `Idempotency-Key` required |
| GET | `/api/v1/trips/{tripId}/join-requests` | Driver of that trip, or admin |
| GET | `/api/v1/me/join-requests` | Signed-in passenger |
| GET | `/api/v1/join-requests/{id}` | A party to the request, or admin. Others get 404 |
| POST | `/api/v1/join-requests/{id}/accept` | Driver, pending only |
| POST | `/api/v1/join-requests/{id}/reject` | Driver, pending only |
| POST | `/api/v1/join-requests/{id}/cancel` | Passenger, pending or accepted |

`GET /me/trips?role=passenger` is no longer empty. `GET /users/{id}/public-profile` adds
`cancellationsLast90Days`.

## Database

Alembic `0005_trip_join_requests` (revises `0004`): `trip_join_requests` with status and
cancelled-by enums, seat and fraction checks, `RESTRICT` foreign keys, a partial unique index on
the active (trip, passenger) pair, and a unique index on (passenger, idempotency key).

## Permissions

`join_requests:create`, `:cancel`, and `:list_mine` belong to `PASSENGER` and `DRIVER`.
`:accept`, `:reject`, and `:list_for_trip` belong to `DRIVER` (`:list_for_trip` also to `ADMIN`).
`:read` is any signed-in role, and the service still returns 404 unless the caller is a party or
an admin. An admin who is not the passenger cannot create, accept, reject, or cancel.

## Explicitly not in this phase

| Item | Why |
| --- | --- |
| In-app and email notifications for requests | Phase 7. The API logs `notification=JOIN_REQUEST_*` |
| 24 h and 2 h unanswered-request reminders | Phase 7. Expiry at departure is implemented |
| Trip chat membership on accept | Phase 7 |
| Block exclusion on create (`BR-JOIN-01`) | Phase 8 — no `user_blocks` table, so the check is a no-op |
| Ratings and `minRating` | Phase 8 |

## Quality gate

Recorded in `docs/project-status.md` §Phase 6 gate. Playwright join journeys stay deferred to
the combined product-owner test pass, same as Phase 5.

## How to try it locally

1. Infrastructure: `pnpm infra:up` (Postgres on host port 5433, Redis, MinIO, Mailpit).
2. API: `cd apps/api; python -m uv run alembic upgrade head` then
   `python -m uv run uvicorn app.main:create_app --factory --reload --port 8000`.
3. Web: `pnpm dev` → http://localhost:3000/ar
4. Publish a trip as an approved driver (El Obour → Nasr City, then **نشر**).
5. Sign in as a passenger whose email is verified and whose identity is approved. Open the trip.
   Set pickup and drop-off on the route, then send the request.
6. Sign back in as the driver. The same trip lists the request with the passenger's name, seat
   count, identity badge, and cancellations in the last 90 days. **قبول** reserves the seats.
7. The passenger's requests live at **طلباتي** (`/ar/me/requests`). Accepted trips also appear
   under **رحلات راكبها** on `/ar/me/trips`.
