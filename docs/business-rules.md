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
| BR-ACC-01 | The primary account identifier is a unique **email address** (OD-004 approved 2026-10-01, option c). A phone number may be stored but is **never verified and never used to authenticate** until an SMS provider is separately approved. Every new account receives role `PASSENGER` and status `ACTIVE`; the email starts unverified (BR-AUTH-05). |
| BR-ACC-02 | Role `DRIVER` is granted only by the system when a driver verification transitions to `APPROVED`, and revoked when an admin revokes driver status. It is never self-assigned. |
| BR-ACC-03 | Role `ADMIN` is granted/revoked only by an existing `ADMIN`; the action is audited. The first admin is created by a controlled bootstrap command, never through the public API. |
| BR-ACC-04 | A single account may hold `PASSENGER` and `DRIVER` simultaneously, and the UI exposes both modes to such users (OD-013 approved 2026-10-01): the driver area becomes available as soon as the `DRIVER` role is held; no separate account is ever created. |
| BR-ACC-05 | Users in status `SUSPENDED`, `DEACTIVATED` or `DELETED` cannot authenticate; existing sessions are revoked on transition. |
| BR-ACC-06 | Suspending a driver with `PUBLISHED`/`FULL` trips cancels those trips with reason `DRIVER_SUSPENDED` and notifies passengers. |
| BR-ACC-07 | Account deletion (OD-020 approved 2026-10-01): a user may delete their own account only when they have no trips in `PUBLISHED`/`FULL`/`IN_PROGRESS` and no join requests in `ACCEPTED` (otherwise `DELETE_BLOCKED` listing the blockers). Deletion sets status `DELETED`, revokes every session and starts a grace period of `accounts.deletion_grace_days` (14); a successful login during the grace period restores status `ACTIVE` and cancels anonymisation. After the grace period a job anonymises the account per `database.md` §7. Audit logs are always retained; ratings and messages are kept but attributed to an anonymised user. |
| BR-ACC-08 | Registration requires the user to be at least `accounts.minimum_age_years` (18) based on a supplied date of birth, and to explicitly accept the current terms of service and privacy policy; the accepted versions and timestamp are stored on the account (OD-021 approved 2026-10-01). Re-acceptance after a version change is a later phase and is not silently assumed. |

## 1.1 Authentication & sessions

Mechanisms are specified in ADR-0004 and `security.md` §1; the rules below are the behaviour the
API must enforce.

| ID | Rule |
| --- | --- |
| BR-AUTH-01 | Passwords are between `auth.password_min_length` (10) and 128 characters, hashed with Argon2id over an HMAC pepper. No composition rules; the password is never logged, returned or emailed. |
| BR-AUTH-02 | A successful login issues an access token (TTL `auth.access_token_ttl_seconds`) and an opaque refresh session (sliding `auth.refresh_token_ttl_days`, absolute `auth.refresh_absolute_ttl_days`). Every refresh rotates the token; presenting an already-rotated token revokes the whole session family and is audited as a reuse detection. |
| BR-AUTH-03 | Only `ACTIVE` accounts may authenticate (BR-ACC-05); any other status fails with a generic error. Login errors never reveal whether the email exists, and registration/forgot-password respond identically for existing and unknown identifiers. |
| BR-AUTH-04 | Email verification uses a single-use token hashed at rest with TTL `auth.email_verification_ttl_hours` (24). Re-sending invalidates previous tokens for that user and is rate-limited. |
| BR-AUTH-05 | An account with an unverified email may sign in, read and edit its own profile, and browse public content, but may **not** publish a trip or create a join request (`EMAIL_NOT_VERIFIED`). Derived from the OD-004 approval; the alternative (blocking login) was rejected because it hides the resend flow. |
| BR-AUTH-06 | Password reset uses a single-use hashed token with TTL `auth.password_reset_ttl_minutes` (60). Using it sets the new password and revokes **all** sessions of that user. |
| BR-AUTH-07 | Changing a password requires the current password and revokes all sessions except the one performing the change. |
| BR-AUTH-08 | A user can list their own sessions (device label, hashed IP, created/last used) and revoke any of them individually or all except the current one. Revocation takes effect immediately for refresh and within the access-token TTL for reads. |
| BR-AUTH-09 | Logout revokes the current session server-side and clears the authentication cookies; it is idempotent. |

## 2. Verification

| ID | Rule |
| --- | --- |
| BR-VER-01 | Identity verification statuses: `NOT_SUBMITTED → PENDING → APPROVED | REJECTED`; `REJECTED → PENDING` on resubmission. |
| BR-VER-02 | Driver verification follows the same state machine plus a terminal `APPROVED → REVOKED` transition performed by an admin (BR-ACC-02, moderation action `REVOKE_DRIVER`), and additionally requires at least one vehicle with all required documents submitted (OD-024 approved 2026-10-02: `REGISTRATION_FRONT` + `REGISTRATION_BACK`; `VEHICLE_PHOTO` optional). Identity must already be `APPROVED` (BR-VER-05). Reviewer is `ADMIN` only; the UI shows a 48-hour target (`verification.review_sla_hours`). A revoked driver may reapply, creating a new `PENDING` record. |
| BR-VER-03 | Approval/rejection requires role `ADMIN`, a reason on rejection, and produces an audit entry and a notification. |
| BR-VER-04 | Viewing a verification document produces an audit entry (`DOCUMENT_VIEWED`) with actor, document id and request id. |
| BR-VER-05 | Identity verification is **mandatory for passengers before creating their first join request** and mandatory for drivers (OD-002 approved 2026-10-01, option b; flag `verification.identity_required_before_join`). Browsing and searching do not require it. Required documents: `NATIONAL_ID_FRONT`, `NATIONAL_ID_BACK`, `SELFIE`. |
| BR-VER-06 | Documents are retained for 30 days after the decision (`verification.document_retention_days`, OD-009 approved 2026-10-02), then the object is purged; the decision record and reviewer are kept. |
| BR-VER-07 | Driving-licence expiry is collected on the driver application. The driver is notified 30 days before expiry (`verification.licence_expiry_notice_days`); an expired licence blocks publishing a trip until a new application is approved (OD-003 approved 2026-10-02). |
| BR-VEH-01 | A driver may register up to `vehicles.max_per_driver` (3) vehicles. Required vehicle documents are `REGISTRATION_FRONT` and `REGISTRATION_BACK` (OD-024). A vehicle cannot be used on a trip until it is `APPROVED` and the owner holds `DRIVER` (FR-DRV-06). |
| BR-VEH-02 | Licence plates are visible to the owner, to `ADMIN`, and to accepted passengers of a trip that uses that vehicle. They are never shown on public profiles or search (OD-022 approved 2026-10-02). |

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
| `PUBLISHED`/`FULL` | `IN_PROGRESS` | driver | now ≥ departure_at − `trips.start_window_minutes` (OD-017 approved); email verified |
| `PUBLISHED`/`FULL` | `CANCELLED` | driver, admin | reason required for admin; see BR-TRIP-06 |
| `PUBLISHED`/`FULL` | `EXPIRED` | system job | now > departure_at + `trips.expire_grace_minutes` and not started |
| `IN_PROGRESS` | `COMPLETED` | driver or system | driver any time after start; system at `estimated_arrival_at + trips.auto_complete_hours` (OD-017 approved) |
| `IN_PROGRESS` | `CANCELLED` | driver, admin | reason required |

No other transitions exist. Terminal states: `COMPLETED`, `CANCELLED`, `EXPIRED`.

### 3.2 Rules

| ID | Rule |
| --- | --- |
| BR-TRIP-01 | Only users with role `DRIVER` and status `ACTIVE` can create trips. |
| BR-TRIP-02 | `total_seats` is the number of passenger seats offered (excludes the driver). `1 ≤ total_seats ≤ min(vehicle.seat_capacity − 1, trips.max_passenger_seats)`. Hard cap: 7 (OD-012 approved 2026-10-02). |
| BR-TRIP-03 | `available_seats` starts equal to `total_seats` and is only changed by seat reservation/release (§4). Invariant: `0 ≤ available_seats ≤ total_seats` (DB CHECK). |
| BR-TRIP-04 | `departure_at` must be in the future at publish time (server clock, UTC). `estimated_arrival_at`, when present, must be after `departure_at`. |
| BR-TRIP-05 | A trip has exactly one route (ordered stops: origin, 0..N waypoints, destination) with server-computed geometry from the mapping provider (OD-005 approved: Mapbox, `FakeMapProvider` in tests). Clients never submit geometry. |
| BR-TRIP-06 | Cancelling a trip transitions every `PENDING` and `ACCEPTED` request to `CANCELLED` with `cancelled_by = DRIVER` or `ADMIN` (never `EXPIRED`); seats are not released because the trip is terminal; each affected passenger is notified; the conversation becomes read-only. |
| BR-TRIP-07 | Editing while no acceptances exist: all fields editable except that `total_seats` cannot drop below `total_seats − available_seats` (already-reserved seats). After at least one `ACCEPTED` request (OD-023 approved 2026-10-02): notes and increasing `total_seats` are allowed; a departure shift of more than `trips.edit_departure_tolerance_minutes` (15) or a route/stop change is rejected — cancel and republish. |
| BR-TRIP-08 | A driver cannot have two trips overlapping in time (`departure_at` of one within [departure_at, estimated_arrival_at] of the other) in status `PUBLISHED`/`FULL`/`IN_PROGRESS`. |
| BR-TRIP-09 | Trip price snapshot is computed server-side at publish time from the active pricing rule (§7) and stored on the trip. Client-provided prices are ignored. Drivers cannot override (OD-007 approved: suggested contribution, cash off-platform). |
| BR-TRIP-10 | Passengers see approximate origin/destination (privacy radius `privacy.location_blur_meters` = 500, OD-001 approved) until accepted; exact stop coordinates are visible to the driver, `ADMIN`, and accepted members only. |
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
| BR-JOIN-01 | Requester must be `ACTIVE`, hold `PASSENGER`, have a verified email (BR-AUTH-05), have identity verification `APPROVED` (BR-VER-05), not be the trip's driver, and not be blocked by / blocking the driver. |
| BR-JOIN-02 | Trip must be `PUBLISHED` (not `FULL`) and `1 ≤ seats_requested ≤ min(available_seats, bookings.max_seats_per_request)`. |
| BR-JOIN-03 | At most one request in `PENDING` or `ACCEPTED` per (trip, passenger). Enforced by a partial unique index. |
| BR-JOIN-04 | Pickup and drop-off points must be route-compatible (§5) at request time; the request stores the passenger's points and computed pickup/drop-off route offsets. |
| BR-JOIN-05 | `POST /trips/{id}/join-requests` requires an `Idempotency-Key`; the same key for the same user returns the original result (unique index on `(passenger_id, idempotency_key)`). |
| BR-JOIN-06 | **Acceptance is atomic.** In one transaction: `SELECT … FROM trips WHERE id = ? FOR UPDATE` → verify `available_seats ≥ seats_requested` → `UPDATE trips SET available_seats = available_seats − n` → `UPDATE request SET status='ACCEPTED'` → if `available_seats = 0` set trip `FULL` → enqueue notifications after commit. The DB `CHECK (available_seats >= 0)` is the last line of defence. |
| BR-JOIN-07 | Cancelling an `ACCEPTED` request releases seats in the same locked transaction and transitions `FULL → PUBLISHED` if applicable. |
| BR-JOIN-08 | Accepting a request whose trip is no longer `PUBLISHED`/`FULL` fails with `TRIP_NOT_ACCEPTING`. Accepting an already non-`PENDING` request fails with `REQUEST_NOT_PENDING` (no silent success). |
| BR-JOIN-09 | A `PENDING` request expires at the trip's `departure_at` (OD-014 approved 2026-10-15). The worker job is idempotent. Driver reminders 24 h and 2 h before departure are Phase 7 notifications. |
| BR-JOIN-10 | Cancellations are recorded with actor, timestamp and minutes before departure (OD-008 approved 2026-10-15, option a). Late means `< bookings.late_cancel_minutes` (120). No automatic warning or suspension. Public profiles show the count of the user's own cancellations in the last `bookings.cancellation_window_days` (90). |
| BR-JOIN-11 | When a trip reaches `COMPLETED`, all `ACCEPTED` requests become `COMPLETED`. |

### 4.2 Concurrency scenarios that must be tested (MEP §88)

Two passengers accepting the last seat; driver cancels while a request is pending; passenger
cancels while the driver accepts; duplicate request submissions; duplicate `Idempotency-Key`;
repeated accept calls. See `testing.md` §5.

## 5. Search & route matching

| ID | Rule |
| --- | --- |
| BR-MATCH-01 | Candidate trips: status `PUBLISHED`, `available_seats ≥ seats_requested`, `departure_at` within the passenger's requested window [`t_from`, `t_to`] (defaults: ± `matching.default_time_window_minutes` around the requested time). |
| BR-MATCH-02 | **Geographic compatibility** (PostGIS): pickup point within `matching.corridor_width_meters` of the route line **and** drop-off point within the same distance **and** `ST_LineLocatePoint(route, pickup) < ST_LineLocatePoint(route, dropoff)` (passenger travels in the route's direction). Default width: 1000 (OD-006 approved). |
| BR-MATCH-03 | **Exact match** flag: pickup within `matching.stop_proximity_meters` of a trip stop *and* drop-off within the same distance of a later stop. Shown distinctly from "on the way". |
| BR-MATCH-04 | El Obour → 6th of October is **not** compatible with El Obour → Nasr City unless the route geometry passes within the corridor of Nasr City in the correct order. Compatibility is never inferred from place names. |
| BR-MATCH-05 | Detour-based matching (driver deviates to pick up) is **not** in scope (OD-006 approved: no detour in MVP). |
| BR-MATCH-06 | Ranking is deterministic: order by (1) exact-match first, (2) sum of pickup + drop-off distance to route ascending, (3) absolute time difference to requested time ascending, (4) available seats descending, (5) `departure_at` ascending, (6) trip id. No other signals. Any change requires a documented revision here. |
| BR-MATCH-07 | Results exclude trips whose driver has blocked or is blocked by the searcher. Until Phase 8 there are no blocks, so this clause is a no-op. |
| BR-MATCH-08 | Distances are computed with `geography` types (metres on the spheroid), never with planar lat/lon arithmetic. |
| BR-MATCH-09 | Search and trip detail require a signed-in session (OD-029 approved 2026-10-02). Anonymous callers receive `401 UNAUTHENTICATED`. |

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
| BR-PRICE-05 | The displayed amount is a **suggested contribution** paid in cash off-platform. Drivers cannot set or override it (OD-007 approved 2026-10-02). The UI uses that wording. |
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
| `auth.refresh_absolute_ttl_days` | auth | 90 | ADR-0004 |
| `auth.password_min_length` | auth | 10 | security.md |
| `auth.login_rate_limit` | auth | 10 / 15 min per IP, 5 / 15 min per identifier | security.md |
| `auth.register_rate_limit` | auth | 5 / hour per IP | security.md |
| `auth.forgot_rate_limit` | auth | 3 / hour per identifier, 10 / hour per IP | security.md |
| `auth.email_verification_ttl_hours` | auth | 24 | security.md |
| `auth.password_reset_ttl_minutes` | auth | 60 | conventional |
| `accounts.deletion_grace_days` | users | 14 | OD-020 (approved) |
| `accounts.minimum_age_years` | users | 18 | OD-021 (approved) |
| `legal.terms_version` / `legal.privacy_version` | users | `2026-10-01` | OD-021 (approved) |
| `email.from_address` / `email.from_name` | notifications | `no-reply@fisikkati.local` / `Fi Sikkati` | OD-019 (approved: any SMTP provider behind `EmailSender`) |
| `verification.identity_required_before_join` | verification | true | OD-002 (approved) |
| `uploads.max_document_bytes` | files | 10 MiB | security.md |
| `uploads.allowed_document_mime` | files | `image/jpeg,image/png,application/pdf` | security.md |
| `uploads.signed_url_ttl_seconds` | files | 120 | security.md |
| `verification.document_retention_days` | verification | 30 | OD-009 (approved) |
| `verification.review_sla_hours` | verification | 48 | OD-003 (approved) |
| `verification.licence_expiry_notice_days` | verification | 30 | OD-003 (approved) |
| `vehicles.max_per_driver` | vehicles | 3 | conventional; revisit |
| `trips.max_passenger_seats` | trips | 7 | OD-012 (approved) |
| `trips.expire_grace_minutes` | trips | 60 | OD-017 (approved) |
| `trips.starting_soon_notice_minutes` | trips/notifications | 60 | conventional |
| `trips.start_window_minutes` | trips | 30 | OD-017 (approved) |
| `trips.auto_complete_hours` | trips | 6 | OD-017 (approved) |
| `trips.edit_departure_tolerance_minutes` | trips | 15 | OD-023 (approved) |
| `bookings.max_seats_per_request` | bookings | = `trips.max_passenger_seats` (7) | OD-012 |
| `bookings.pending_request_expiry` | bookings | at `departure_at` | OD-014 (approved) |
| `bookings.cancellation_window_days` | bookings | 90 | OD-008 (approved) |
| `bookings.late_cancel_minutes` | bookings | 120 | OD-008 (approved) |
| `matching.corridor_width_meters` | matching | 1000 | OD-006 (approved) |
| `matching.stop_proximity_meters` | matching | 500 | OD-006 (approved) |
| `matching.default_time_window_minutes` | matching | 60 | OD-006 (approved) |
| `privacy.location_blur_meters` | privacy | 500 | OD-001 (approved) |
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
