# API Changelog

Consumer-facing changes to the HTTP API (`/api/v1`). Breaking changes are marked **BREAKING**
and follow the deprecation policy in `api.md` §Versioning. The authoritative contract is
`packages/types/openapi.json`, regenerated from the FastAPI app in CI.

## Unreleased — Phase 6 (Join requests)

Added

- `POST /trips/{tripId}/join-requests` (`Idempotency-Key` required). Pickup and drop-off must sit
  on the stored route, in order. Identity must be approved and email verified.
- `GET /trips/{tripId}/join-requests` for the driver (and admin). `GET /me/join-requests` for the
  passenger. `GET /join-requests/{id}` for a party only; everyone else gets `404`.
- `POST /join-requests/{id}/accept|reject|cancel`. Accept and cancel of an accepted request lock
  the trip row and change `availableSeats`. A full trip returns to `PUBLISHED` when a seat is
  released. A second accept returns `409 REQUEST_NOT_PENDING`.
- `GET /me/trips?role=passenger` lists trips with an accepted or completed request. Accepted
  passengers see exact stops (`exactStops: true`).
- `GET /users/{id}/public-profile` adds `cancellationsLast90Days`.
- Pending requests expire at the trip departure via the worker. Cancellation stores the actor
  and minutes before departure. No automatic suspension (OD-008/014 approved 2026-10-15).

Not in this phase

- In-app and email notifications for requests, and the 24 h / 2 h unanswered-request reminders —
  Phase 7. The API logs the event name so the notification service can subscribe later.
- Trip chat membership — Phase 7.
- Block exclusion — Phase 8.

## Unreleased — Phase 5 (Search)

Added

- Search: `GET /search/trips` (signed-in, OD-029). Required query: `pickupLat`, `pickupLng`,
  `dropoffLat`, `dropoffLng`, `date` (Africa/Cairo). Optional `time` (± default window),
  `timeFrom`+`timeTo`, `seats`, `verifiedOnly`, `minRating` (empty until Phase 8),
  `vehicleType`, `priceMax` (piastres), `cursor`, `limit`.
- Matching: PostGIS corridor cover + pickup-before-dropoff along the route; `matchKind`
  `EXACT` | `ON_ROUTE`; ranking BR-MATCH-06; results use blurred area points, no plates.
- Rate limit `60/60` per user (`SEARCH_TRIPS_RATE_LIMIT`).
- `GET /api/v1/platform/config` now also returns `matchingCorridorWidthMeters`,
  `matchingStopProximityMeters`, `matchingDefaultTimeWindowMinutes`.

Not in this phase

- Join requests — Phase 6.
- Ratings join for `minRating`, and block exclusion — Phase 8.

## Unreleased — Phase 4 (Trips)

Added

- Maps: `GET /maps/autocomplete`, `GET /maps/geocode`, `POST /maps/route-preview` (signed-in).
  Geometry is computed server-side. Without `MAPBOX_ACCESS_TOKEN` the fake geodesic provider is
  used; with a token, Mapbox Search v6 + Directions.
- Pricing: `GET /pricing/estimate?distanceM=` — integer piastres, label `suggested_contribution`
  (OD-007). Clients cannot override the stored trip price.
- Trips: `POST /trips` (Idempotency-Key), `GET/PATCH /trips/{id}` (`If-Match` version on PATCH),
  `POST /trips/{id}/publish|start|complete|cancel`, `GET /me/trips?role=driver`.
  `role=passenger` is an empty list until Phase 6. Drafts are hidden from non-owners.
  Non-owner coordinates are jittered 500 m (OD-001).
- `GET /api/v1/platform/config` now also returns `maxPassengerSeats`, `suggestedPriceLabel`,
  `mapboxPublicToken`.
- Worker cron every 15 minutes expires unpublished trips (departure + 60 min) and auto-completes
  in-progress trips (estimated arrival + 6 h) (OD-017).
- `DELETE /me` is blocked while the account has a published, full, or in-progress trip.

Not in this phase

- Search / matching (`POST /trips/search`) — delivered in Phase 5 as `GET /search/trips`.
- Join requests and passenger trip list — Phase 6.
- Admin trip console — Phase 9 (admin cancel of another driver's trip is available now).

## Unreleased — Phase 3 (Driver & Vehicle)

Added

- Files: private document store (MinIO / S3-compatible) and public media for profile photos.
  Admins fetch `GET /admin/verifications/files/{fileId}/download-url` (120 s, `DOCUMENT_VIEWED`
  audit). Applicants see metadata only — they cannot re-download their own files.
- Identity: `POST /me/verification/identity/documents` (types `NATIONAL_ID_FRONT`,
  `NATIONAL_ID_BACK`, `SELFIE`), `POST /me/verification/identity/submit`.
- Driver: `POST /me/verification/driver/documents`, `POST /me/verification/driver/submit`
  (`vehicleId`, `licenceExpiresOn`, `licenceFileId`). Identity must already be `APPROVED`.
- Vehicles: `GET/POST /me/vehicles`, `GET/PATCH /me/vehicles/{id}`,
  `POST /me/vehicles/{id}/deactivate`, `POST /me/vehicles/{id}/documents`
  (`REGISTRATION_FRONT`, `REGISTRATION_BACK` required; `VEHICLE_PHOTO` optional). Max 3 active.
- Admin queue (minimal; full admin platform is Phase 9):
  `GET /admin/verifications/identity|driver`, detail + `…/approve` + `…/reject`,
  `GET /admin/vehicles`, detail + `…/approve` + `…/reject` + `…/deactivate`.
- Account: `POST /me/photo` (public bucket). `GET /me` and public profile include `photoUrl`.
- `GET /api/v1/platform/config` now also returns `maxVehiclesPerDriver` and `reviewSlaHours`.
- Nightly worker cron purges private objects whose `purge_after` has elapsed (OD-009, 30 days).

Not in this phase

- In-app notifications (Phase 7). Review outcomes are emailed now.
- Licence-expiry reminder cron (config `verification.licence_expiry_notice_days` is live;
  the 30-day email waits for Phase 7 so we do not spam without a notice ledger).
- Full admin users/trips/settings console (Phase 9).
- Attaching an approved vehicle to a published trip — delivered in Phase 4.

## Unreleased — Phase 2 (Authentication & Identity)

Added

- Auth: `POST /auth/register` (always `202`, anti-enumeration), `POST /auth/login`,
  `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/email/verify`,
  `POST /auth/email/resend`, `POST /auth/password/forgot`, `POST /auth/password/reset`,
  `POST /auth/password/change`.
- Account: `GET /me`, `PATCH /me`, `DELETE /me` (BR-ACC-07 grace-period close),
  `GET /me/sessions`, `DELETE /me/sessions/{session_id}`,
  `GET /users/{userId}/public-profile`.
- `GET /api/v1/platform/config` now also returns `passwordMinLength`, `minimumAgeYears`,
  `termsVersion`, `privacyVersion`, `deletionGraceDays`.
- Cookie session for browsers (`__Host-fs_access`, `__Secure-fs_refresh`, `__Host-fs_csrf`)
  plus `X-CSRF-Token` double-submit (ADR-0004). API clients may send tokens in the body with
  `X-Client-Type: api`.

Not in this phase

- `POST /me/photo`, `GET /me/verification` document upload, `GET/PUT/DELETE /me/blocks` — files,
  verification documents and blocking arrive with Phases 3 and 8.

## Unreleased — Phase 1 (Foundation)

Added

- `GET /health/live` and `GET /health/ready` (outside `/api/v1`, excluded from the OpenAPI
  document). `ready` returns `503` with per-dependency status when PostgreSQL or Redis is
  unreachable.
- `GET /api/v1/platform/config` — public, unauthenticated: `environment`, `apiVersion`,
  `supportedLocales`, `defaultLocale`, `defaultTimezone`.
- Error envelope: every non-2xx response is RFC 9457 Problem Details
  (`application/problem+json`) with a stable `code` (`VALIDATION_ERROR`, `NOT_FOUND`,
  `METHOD_NOT_ALLOWED`, `INTERNAL_ERROR`, …), `requestId` and optional `errors[]` field list.
  Request validation failures return `400`, not FastAPI's default `422`.
- `X-Request-Id` accepted on requests (sanitised) and always returned; exposed to browsers via
  CORS.
- Security headers on every response (`nosniff`, `DENY` framing, referrer policy, COOP/CORP,
  restrictive `Permissions-Policy`, `Cache-Control: no-store`).
- Interactive docs at `/api/v1/docs` and schema at `/api/v1/openapi.json` in
  development/test/staging only.
