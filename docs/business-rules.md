# Business Rules

Every rule the backend enforces. Rules are numbered `BR-<domain>-<n>` and are referenced from
code, tests and the PRD. **A rule that is not in this document is not a rule.** Anything
marked `⛔ OD-xxx` is an unresolved decision: the code must stop at that boundary and must not
guess (MEP §4).

Configuration keys are listed in §10 and live in server-side configuration, never as scattered
constants (MEP §70).

---

## 1. Accounts & roles

| ID | Rule |
| --- | --- |
| BR-ACC-01 | Every new account receives role `PASSENGER` and status `ACTIVE` (subject to identifier verification per ⛔ OD-004). |
| BR-ACC-02 | Role `DRIVER` is granted only by the system when a driver verification transitions to `APPROVED`, and revoked when an admin revokes driver status. It is never self-assigned. |
| BR-ACC-03 | Role `ADMIN` is granted/revoked only by an existing `ADMIN`; the action is audited. The first admin is created by a controlled bootstrap command, never through the public API. |
| BR-ACC-04 | A single account may hold `PASSENGER` and `DRIVER` simultaneously. Exposing "both modes" in the UI: ⛔ OD-013. |
| BR-ACC-05 | Users in status `SUSPENDED`, `DEACTIVATED` or `DELETED` cannot authenticate; existing sessions are revoked on transition. |
| BR-ACC-06 | Suspending a driver with `PUBLISHED`/`FULL` trips cancels those trips with reason `DRIVER_SUSPENDED` and notifies passengers. |
| BR-ACC-07 | Account deletion policy: ⛔ OD-020. Technical mechanism (anonymisation, retention of audit logs) is designed in `database.md` §7. |
| BR-ACC-08 | Minimum age / legal acceptance: ⛔ OD-021. |

## 2. Verification

| ID | Rule |
| --- | --- |
| BR-VER-01 | Identity verification statuses: `NOT_SUBMITTED → PENDING → APPROVED | REJECTED`; `REJECTED → PENDING` on resubmission. |
| BR-VER-02 | Driver verification follows the same state machine plus a terminal `APPROVED → REVOKED` transition performed by an admin (BR-ACC-02, moderation action `REVOKE_DRIVER`), and additionally requires at least one vehicle with all required documents submitted (⛔ OD-024 defines the list). A revoked driver may reapply, creating a new `PENDING` record. |
| BR-VER-03 | Approval/rejection requires role `ADMIN`, a reason on rejection, and produces an audit entry and a notification. |
| BR-VER-04 | Viewing a verification document produces an audit entry (`DOCUMENT_VIEWED`) with actor, document id and request id. |
| BR-VER-05 | Whether identity verification is mandatory for passengers before requesting a seat: ⛔ OD-002. Whether it is mandatory for drivers: yes (MEP §9/§10 — drivers must be verified). |
| BR-VER-06 | Documents are retained for the approved period after decision, then deleted; the decision record is kept: ⛔ OD-009. |

## 3. Trips

### 3.1 State machine

```
DRAFT ──publish──▶ PUBLISHED ◀──seat released── FULL
                    │   ▲                        ▲
                    │   └──────seats reach 0─────┘
                    │
   ┌────────────────┼──────────────────────┐
   │                │                      │
 start            cancel                 departure passed + grace
   ▼                ▼                      ▼
IN_PROGRESS ─complete─▶ COMPLETED      EXPIRED
   │
 cancel
   ▼
CANCELLED
```

| From | To | Actor | Conditions |
| --- | --- | --- | --- |
| `DRAFT` | `PUBLISHED` | driver | vehicle `ACTIVE` + `APPROVED`; departure in future; 1 ≤ total_seats ≤ `trips.max_passenger_seats`; route present |
| `DRAFT` | `CANCELLED` | driver | — |
| `PUBLISHED` | `FULL` | system | available_seats becomes 0 |
| `FULL` | `PUBLISHED` | system | available_seats becomes > 0 |
| `PUBLISHED`/`FULL` | `IN_PROGRESS` | driver | ⛔ OD-017 (window around departure, manual vs automatic) |
| `PUBLISHED`/`FULL` | `CANCELLED` | driver, admin | reason required for admin; see BR-TRIP-06 |
| `PUBLISHED`/`FULL` | `EXPIRED` | system job | now > departure_at + `trips.expire_grace_minutes` and not started |
| `IN_PROGRESS` | `COMPLETED` | driver | ⛔ OD-017 (manual vs automatic timeout) |
| `IN_PROGRESS` | `CANCELLED` | driver, admin | reason required |

No other transitions exist. Terminal states: `COMPLETED`, `CANCELLED`, `EXPIRED`.

### 3.2 Rules

| ID | Rule |
| --- | --- |
| BR-TRIP-01 | Only users with role `DRIVER` and status `ACTIVE` can create trips. |
| BR-TRIP-02 | `total_seats` is the number of passenger seats offered (excludes the driver). `1 ≤ total_seats ≤ min(vehicle.seat_capacity − 1, trips.max_passenger_seats)`. Default hard cap: ⛔ OD-012. |
| BR-TRIP-03 | `available_seats` starts equal to `total_seats` and is only changed by seat reservation/release (§4). Invariant: `0 ≤ available_seats ≤ total_seats` (DB CHECK). |
| BR-TRIP-04 | `departure_at` must be in the future at publish time (server clock, UTC). `estimated_arrival_at`, when present, must be after `departure_at`. |
| BR-TRIP-05 | A trip has exactly one route (ordered stops: origin, 0..N waypoints, destination) with server-computed geometry from the mapping provider (⛔ OD-005). Clients never submit geometry. |
| BR-TRIP-06 | Cancelling a trip transitions every `PENDING` and `ACCEPTED` request to `CANCELLED` with `cancelled_by = DRIVER` or `ADMIN` (never `EXPIRED`); seats are not released because the trip is terminal; each affected passenger is notified; the conversation becomes read-only. |
| BR-TRIP-07 | Editing rules after at least one `ACCEPTED` request: ⛔ OD-023. Editing while no acceptances exist: all fields editable except that `total_seats` cannot drop below `total_seats − available_seats` (already-reserved seats). |
| BR-TRIP-08 | A driver cannot have two trips overlapping in time (`departure_at` of one within [departure_at, estimated_arrival_at] of the other) in status `PUBLISHED`/`FULL`/`IN_PROGRESS`. |
| BR-TRIP-09 | Trip price snapshot is computed server-side at publish time from the active pricing rule (§7) and stored on the trip. Client-provided prices are ignored. Whether the driver may override: ⛔ OD-007. |
| BR-TRIP-10 | Passengers see approximate origin/destination (privacy radius `privacy.location_blur_meters`, ⛔ OD-001 for value) until accepted; exact stop coordinates are visible to accepted members only. |
| BR-TRIP-11 | Recurring trips: ⛔ OD-018 — not supported. |

## 4. Join requests & seat consistency (critical)

### 4.1 State machine

```
PENDING ──accept──▶ ACCEPTED ──trip completed──▶ COMPLETED
   │                   │
   ├─reject─▶ REJECTED ├─passenger/driver cancel─▶ CANCELLED
   ├─cancel─▶ CANCELLED│
   └─expire─▶ EXPIRED  └─trip cancelled──────────▶ CANCELLED
```

| ID | Rule |
| --- | --- |
| BR-JOIN-01 | Requester must be `ACTIVE`, hold `PASSENGER`, not be the trip's driver, not be blocked by / blocking the driver, and (⛔ OD-002) be identity-verified if required. |
| BR-JOIN-02 | Trip must be `PUBLISHED` (not `FULL`) and `1 ≤ seats_requested ≤ min(available_seats, bookings.max_seats_per_request)`. |
| BR-JOIN-03 | At most one request in `PENDING` or `ACCEPTED` per (trip, passenger). Enforced by a partial unique index. |
| BR-JOIN-04 | Pickup and drop-off points must be route-compatible (§5) at request time; the request stores the passenger's points and computed pickup/drop-off route offsets. |
| BR-JOIN-05 | `POST /trips/{id}/join-requests` requires an `Idempotency-Key`; the same key for the same user returns the original result (unique index on `(passenger_id, idempotency_key)`). |
| BR-JOIN-06 | **Acceptance is atomic.** In one transaction: `SELECT … FROM trips WHERE id = ? FOR UPDATE` → verify `available_seats ≥ seats_requested` → `UPDATE trips SET available_seats = available_seats − n` → `UPDATE request SET status='ACCEPTED'` → if `available_seats = 0` set trip `FULL` → enqueue notifications after commit. The DB `CHECK (available_seats >= 0)` is the last line of defence. |
| BR-JOIN-07 | Cancelling an `ACCEPTED` request releases seats in the same locked transaction and transitions `FULL → PUBLISHED` if applicable. |
| BR-JOIN-08 | Accepting a request whose trip is no longer `PUBLISHED`/`FULL` fails with `TRIP_NOT_ACCEPTING`. Accepting an already non-`PENDING` request fails with `REQUEST_NOT_PENDING` (no silent success). |
| BR-JOIN-09 | Pending-request expiry (at departure? after N hours?): ⛔ OD-014. Mechanism: background job, idempotent. |
| BR-JOIN-10 | Cancellation windows, limits and consequences (for passengers and drivers): ⛔ OD-008. The system records every cancellation with actor, timestamp and time-before-departure so any policy can be applied later. |
| BR-JOIN-11 | When a trip reaches `COMPLETED`, all `ACCEPTED` requests become `COMPLETED`. |

### 4.2 Concurrency scenarios that must be tested (MEP §88)

Two passengers accepting the last seat; driver cancels while a request is pending; passenger
cancels while the driver accepts; duplicate request submissions; duplicate `Idempotency-Key`;
repeated accept calls. See `testing.md` §5.

## 5. Search & route matching

| ID | Rule |
| --- | --- |
| BR-MATCH-01 | Candidate trips: status `PUBLISHED`, `available_seats ≥ seats_requested`, `departure_at` within the passenger's requested window [`t_from`, `t_to`] (defaults: ± `matching.default_time_window_minutes` around the requested time). |
| BR-MATCH-02 | **Geographic compatibility** (PostGIS): pickup point within `matching.corridor_width_meters` of the route line **and** drop-off point within the same distance **and** `ST_LineLocatePoint(route, pickup) < ST_LineLocatePoint(route, dropoff)` (passenger travels in the route's direction). Default width: ⛔ OD-006. |
| BR-MATCH-03 | **Exact match** flag: pickup within `matching.stop_proximity_meters` of a trip stop *and* drop-off within the same distance of a later stop. Shown distinctly from "on the way". |
| BR-MATCH-04 | El Obour → 6th of October is **not** compatible with El Obour → Nasr City unless the route geometry passes within the corridor of Nasr City in the correct order. Compatibility is never inferred from place names. |
| BR-MATCH-05 | Detour-based matching (driver deviates to pick up) is **not** in scope until ⛔ OD-006 approves a detour limit. |
| BR-MATCH-06 | Ranking is deterministic: order by (1) exact-match first, (2) sum of pickup + drop-off distance to route ascending, (3) absolute time difference to requested time ascending, (4) available seats descending, (5) `departure_at` ascending, (6) trip id. No other signals. Any change requires a documented revision here. |
| BR-MATCH-07 | Results exclude trips whose driver has blocked or is blocked by the searcher. |
| BR-MATCH-08 | Distances are computed with `geography` types (metres on the spheroid), never with planar lat/lon arithmetic. |
| BR-MATCH-09 | Unauthenticated search visibility: ⛔ OD-029. |

## 6. Communication

| ID | Rule |
| --- | --- |
| BR-CHAT-01 | Each trip has exactly one `TRIP` conversation created on publish; the driver is the first member. |
| BR-CHAT-02 | A passenger becomes a member when their request becomes `ACCEPTED`; membership becomes read-only (`left_at` set) when the request becomes `CANCELLED`/`REJECTED`/`COMPLETED` + `chat.post_completion_open_hours`. |
| BR-CHAT-03 | Only active members may post. Message body: 1–`chat.max_message_length` characters, text only. |
| BR-CHAT-04 | Message rate limit per user: `chat.rate_limit_per_minute`. |
| BR-CHAT-05 | System messages are authored by `sender_id = NULL, kind = SYSTEM` and cannot be posted by clients. |
| BR-CHAT-06 | Blocked pairs cannot share a conversation: a block prevents new requests; existing shared memberships are frozen for the blocking pair. |
| BR-CHAT-07 | Phone number exchange: ⛔ OD-011. Community chat scope: ⛔ OD-015. |

## 7. Pricing (display only — no payments)

| ID | Rule |
| --- | --- |
| BR-PRICE-01 | All amounts are integers in minor units (piastres); currency `EGP`. No floating point anywhere in financial code. |
| BR-PRICE-02 | A `pricing_rules` row defines `base_fee_minor`, `per_km_minor`, `platform_fee_percent_bps` (basis points, 0 in MVP), `currency`, `effective_from`, `effective_to`. Exactly one rule is active at a given instant (exclusion constraint). |
| BR-PRICE-03 | Initial seeded values reflect the *concept* in MEP §32: base 1000 (10 EGP), per-km 300 (3 EGP). These are configuration, not law. |
| BR-PRICE-04 | `passenger_price_minor = base_fee_minor + round(per_km_minor × distance_km)` computed server-side per seat from the route distance at publish time; `platform_fee` and `driver_amount` are computed but not charged. |
| BR-PRICE-05 | What the price *means* in MVP (suggested contribution paid in cash off-platform? fixed?), and whether drivers may set/override it: ⛔ OD-007. Until decided the UI labels the price "estimated contribution" only if OD-007 approves that wording; otherwise price display is BLOCKED. |
| BR-PRICE-06 | No payment, refund, wallet or payout records are created (MEP §31, §33). |

## 8. Ratings & trust

| ID | Rule |
| --- | --- |
| BR-RATE-01 | Rating allowed only when trip is `COMPLETED`, rater and ratee were both on the trip (driver ↔ `COMPLETED` passenger), rater ≠ ratee, and no prior rating for (trip, rater, ratee). Enforced by a unique constraint. |
| BR-RATE-02 | Rating window closes `ratings.window_days` after completion. |
| BR-RATE-03 | Dimensions, comment visibility and minimum count before a public average is shown: ⛔ OD-016. Overall score 1–5 integer is fixed. |
| BR-RATE-04 | No composite trust score is computed or displayed (MEP §25). Displayed indicators: verified identity, verified driver, completed trips, average rating (after minimum), account age. |

## 9. Safety, reports, moderation, audit

| ID | Rule |
| --- | --- |
| BR-SAFE-01 | Report targets: `USER`, `TRIP`, `MESSAGE`. Reporter must be authenticated; one open report per (reporter, target). Rate limit `reports.per_user_per_day`. |
| BR-SAFE-02 | Report lifecycle: `OPEN → UNDER_REVIEW → RESOLVED | DISMISSED`. Only `ADMIN` transitions after `OPEN`. |
| BR-SAFE-03 | Moderation actions: `WARN`, `REMOVE_CONTENT`, `SUSPEND_USER`, `RESTORE_USER`, `CANCEL_TRIP`, `REVOKE_DRIVER`. Each is linked to a report (optional), has a reason, and writes an audit entry. Escalation thresholds/strikes: ⛔ OD-010. |
| BR-SAFE-04 | Blocking is unilateral and immediate; the blocked user is not told. |
| BR-SAFE-05 | Audit log is append-only; application DB role has no `UPDATE`/`DELETE` on `audit_logs`. Audited actions are enumerated in `security.md` §9. |

## 10. Configuration keys

All keys are read from server configuration (environment / settings table per key) with the
defaults below **only where the master prompt or an ADR defines them**. Keys marked ⛔ have no
default until the referenced OD is approved and the service refuses to start the affected
feature without an explicit value.

| Key | Domain | Default | Source |
| --- | --- | --- | --- |
| `auth.access_token_ttl_seconds` | auth | 900 | ADR-0004 |
| `auth.refresh_token_ttl_days` | auth | 30 | ADR-0004 |
| `auth.password_min_length` | auth | 10 | security.md |
| `auth.login_rate_limit` | auth | 10 / 15 min per IP+identifier | security.md |
| `uploads.max_document_bytes` | files | 10 MiB | security.md |
| `uploads.allowed_document_mime` | files | `image/jpeg,image/png,application/pdf` | security.md |
| `uploads.signed_url_ttl_seconds` | files | 120 | security.md |
| `verification.document_retention_days` | verification | ⛔ OD-009 | — |
| `vehicles.max_per_driver` | vehicles | 3 | conventional; revisit |
| `trips.max_passenger_seats` | trips | ⛔ OD-012 | — |
| `trips.expire_grace_minutes` | trips | 60 | conventional |
| `trips.starting_soon_notice_minutes` | trips/notifications | 60 | conventional |
| `trips.start_window_minutes` | trips | ⛔ OD-017 | — |
| `bookings.max_seats_per_request` | bookings | = `trips.max_passenger_seats` | — |
| `bookings.pending_request_expiry` | bookings | ⛔ OD-014 | — |
| `bookings.cancellation_policy` | bookings | ⛔ OD-008 | — |
| `matching.corridor_width_meters` | matching | ⛔ OD-006 | — |
| `matching.stop_proximity_meters` | matching | ⛔ OD-006 | — |
| `matching.default_time_window_minutes` | matching | ⛔ OD-006 | — |
| `privacy.location_blur_meters` | privacy | ⛔ OD-001 | — |
| `chat.max_message_length` | chat | 2000 | conventional |
| `chat.rate_limit_per_minute` | chat | 30 | conventional |
| `chat.post_completion_open_hours` | chat | 24 | conventional |
| `pricing.*` | pricing | seeded rule 1000 / 300 / 0 bps | MEP §32 (concept) |
| `ratings.window_days` | ratings | 14 | conventional |
| `reports.per_user_per_day` | safety | 10 | conventional |
| `ai.enabled` | ai | false | feature flag |
| `ai.rate_limit_per_user_per_hour` | ai | 30 | conventional |

"Conventional" defaults are minor implementation details (MEP §98) chosen as the most common
production values; they are configurable and listed here so nothing is hidden. Anything
affecting money, safety, privacy or matching semantics is an OD, not a default.
