# Open Decisions

Unresolved product/business decisions (MEP §4, §92, §96). **Nothing here is implemented until
its status is `APPROVED`**; code stops at the boundary and reports the feature as BLOCKED.
Recommendations are engineering recommendations only. When a decision is approved, record the
decision, approver and date, move the rule into `business-rules.md`, and set the configuration
key.

Statuses: `OPEN`, `APPROVED`, `REJECTED`, `DEFERRED`.

Blocks-phase column shows the first phase that cannot be *completed* without the decision.

| ID | Question | Blocks | Status |
| --- | --- | --- | --- |
| OD-001 | Location privacy: blur radius and exact-location visibility | 5 | APPROVED 2026-10-02 |
| OD-002 | Passenger identity verification policy | 2 | APPROVED 2026-10-01 |
| OD-003 | Driver verification policy | 3 | APPROVED 2026-10-02 |
| OD-004 | Primary account identifier and phone verification (SMS) | 2 | APPROVED 2026-10-01 |
| OD-005 | Mapping provider | 4 | APPROVED 2026-10-02 |
| OD-006 | Route-matching thresholds | 5 | APPROVED 2026-10-02 |
| OD-007 | Meaning of price in MVP and driver override | 4 | APPROVED 2026-10-02 |
| OD-008 | Cancellation windows and consequences | 6 | APPROVED 2026-10-15 |
| OD-009 | Sensitive document retention period | 3 | APPROVED 2026-10-02 |
| OD-010 | Moderation policy (strikes, escalation) | 8 | APPROVED 2026-10-19 |
| OD-011 | Phone number sharing after acceptance | 7 | APPROVED 2026-10-19 |
| OD-012 | Maximum passenger seats per trip | 4 | APPROVED 2026-10-02 |
| OD-013 | Dual-mode accounts in UI | 2 | APPROVED 2026-10-01 |
| OD-014 | Pending join-request expiry | 6 | APPROVED 2026-10-15 |
| OD-015 | Community chat in MVP | 7 | APPROVED 2026-10-19 (defer community rooms) |
| OD-016 | Rating dimensions and visibility | 8 | APPROVED 2026-10-19 |
| OD-017 | Trip start/complete semantics | 4 | APPROVED 2026-10-02 |
| OD-018 | Recurring trips | — | DEFERRED |
| OD-019 | Transactional email provider | 2 | APPROVED 2026-10-01 |
| OD-020 | Account deletion policy | 2 (delete endpoint) / 8 | APPROVED 2026-10-01 |
| OD-021 | Minimum age and legal acceptance | 2 | APPROVED 2026-10-01 |
| OD-022 | Licence plate visibility | 3 | APPROVED 2026-10-02 |
| OD-023 | Trip editing after acceptances | 4 | APPROVED 2026-10-02 |
| OD-024 | Required vehicle documents | 3 | APPROVED 2026-10-02 |
| OD-025 | AI provider and behaviour policy | 10 | APPROVED 2026-10-19 |
| OD-026 | Production hosting provider | 12 | OPEN |
| OD-027 | Domain name | 12 | OPEN |
| OD-028 | Multi-community scoping | — | DEFERRED |
| OD-029 | Search/trip visibility for unauthenticated visitors | 5 | APPROVED 2026-10-02 |
| OD-030 | Product analytics tooling and consent | 11 | APPROVED 2026-10-19 (first-party counters only) |
| OD-031 | Brand wordmark vs product name | 12 (before launch) | APPROVED 2026-10-01 |

---

### OD-001 — Location privacy policy

- **Question**: How much of a trip's origin/destination/pickup location is visible to users who
  are not parties to the trip, and what blur radius is applied?
- **Context**: MEP §21–§22 forbid exposing exact home addresses and require approximate pickup
  locations. Search results and trip detail pages must show *something* useful (BR-TRIP-10).
- **Options**: (a) show area name only, no map pin; (b) deterministic jitter within R metres,
  R ∈ {200, 500, 1000}; (c) snap to nearest named landmark/zone centroid.
- **Recommendation**: (b) with `privacy.location_blur_meters = 500` and area label; exact stop
  coordinates only to accepted parties. Deterministic per-trip jitter prevents averaging attacks.
- **Impact**: search UI, trip detail privacy filtering, `trips.origin_area_point` computation.
- **Decision**: APPROVED (option b, 500 m) by the product owner on 2026-10-02. Configuration key
  `privacy.location_blur_meters = 500`. Exact stop coordinates are shown only to the driver,
  `ADMIN`, and accepted trip parties (Phase 6). Everyone else sees the deterministic per-trip
  jittered area point. Recorded as BR-TRIP-10.

### OD-002 — Passenger identity verification policy

- **Question**: Must passengers verify identity? Before what action? Which documents?
- **Context**: MEP §9 says verification "may include national ID…". Requiring ID from every
  passenger raises trust but adds friction and sensitive-data volume.
- **Options**: (a) optional, badge only; (b) required before first join request; (c) required at
  registration.
- **Recommendation**: (b) — trust before sharing a car, but frictionless browsing. Documents:
  national ID front + back + selfie. Rationale: minimal set that lets an admin confirm identity.
- **Impact**: BR-JOIN-01, onboarding flow, admin queue volume, retention (OD-009).
- **Decision**: APPROVED (option b) by the product owner on 2026-10-01. Recorded as BR-VER-05 and
  BR-JOIN-01; configuration key `verification.identity_required_before_join = true`; document
  types `NATIONAL_ID_FRONT`, `NATIONAL_ID_BACK`, `SELFIE`.

### OD-003 — Driver verification policy

- **Question**: Which documents, who reviews, review SLA, expiry handling?
- **Options**: documents: driving licence (mandatory) + national ID + vehicle registration
  (OD-024); reviewer: ADMIN only (MVP) vs future MODERATOR; SLA: 48 h target shown to user;
  expiry: licence expiry date collected and driver notified 30 days before.
- **Recommendation**: licence + ID + registration; ADMIN reviews; 48 h target; expiry
  notifications. Re-verification on document expiry.
- **Impact**: `driver_verifications` document types, admin UI, notification types.
- **Decision**: APPROVED (recommended option) by the product owner on 2026-10-02. Reviewer is
  `ADMIN` only in MVP; review SLA shown to the applicant is
  `verification.review_sla_hours = 48`. Driving licence is mandatory; identity must already be
  `APPROVED` (BR-VER-05); vehicle registration follows OD-024. Licence expiry is collected and
  the driver is notified 30 days before (`verification.licence_expiry_notice_days = 30`).
  Recorded as BR-VER-02 and BR-VER-07.

### OD-004 — Primary account identifier and phone verification

- **Question**: Is the account identifier email or phone number? Is phone verification (SMS
  OTP) required? MEP §20 says SMS only if explicitly approved.
- **Context**: In Egypt phone numbers are the natural identity and the WhatsApp community is
  phone-based; SMS costs money and requires a vendor (approval).
- **Options**: (a) email + password primary, phone collected unverified; (b) phone + password
  primary with SMS OTP verification (needs SMS vendor approval); (c) email primary now, phone
  OTP added later as an additional factor.
- **Recommendation**: (c). Email is free to verify (OD-019) and unblocks Phase 2 immediately;
  schema already allows either to be primary; SMS can be enabled later without migration.
- **Impact**: registration form, `users.email` nullability, verification flows, rate limits.
- **Decision**: APPROVED (option c) by the product owner on 2026-10-01. `users.email` is
  `NOT NULL UNIQUE`; a phone number may be stored but is never verified and never used to
  authenticate until an SMS provider is separately approved. Recorded as BR-ACC-01 and
  BR-AUTH-01…BR-AUTH-09.

### OD-005 — Mapping provider

- **Question**: Google Maps Platform, Mapbox, or OpenStreetMap-based (e.g. self-hosted
  OSRM/Nominatim or a hosted OSM provider) for autocomplete, geocoding, routing and tiles?
- **Context**: External vendor selection requires approval (MEP §96). Egypt coverage quality
  for autocomplete/Arabic place names matters. Costs scale with search volume.
- **Options**: Google (best Egyptian POI/Arabic coverage, highest cost, strict caching terms);
  Mapbox (good, cheaper, permissive tiles); OSM stack (free, self-hosting burden, weaker
  Arabic POI search).
- **Recommendation**: Mapbox for tiles + geocoding + directions in MVP behind the `MapProvider`
  abstraction; evaluate Google if autocomplete quality is insufficient in El Obour. Fake
  provider for tests regardless.
- **Impact**: Phase 4/5, API keys, CSP origins, cost.
- **Decision**: APPROVED (Mapbox behind `MapProvider`) by the product owner on 2026-10-02.
  Tests and local development without a token use `FakeMapProvider` (deterministic El Obour /
  Cairo fixtures and geodesic routes). A Mapbox token is required before production traffic.
  Clients never submit geometry (BR-TRIP-05).

### OD-006 — Route-matching thresholds

- **Question**: Default corridor width, stop-proximity radius, default time window, detour
  allowance.
- **Options**: corridor 500 m / 1 km / 2 km; stop proximity 300 m / 500 m; time window ±30 /
  ±60 / ±120 min; detour 0 (none) vs ≤ 10 % extra distance.
- **Recommendation**: corridor 1,000 m, stop proximity 500 m, time window ±60 min, **no detour**
  in MVP. Urban Cairo roads are dense; 1 km catches parallel arterials without matching
  different districts. Revisit with real data.
- **Impact**: `trip_routes.corridor` buffer, BR-MATCH-02/03, search UX.
- **Decision**: APPROVED (recommended values) by the product owner on 2026-10-02. Corridor
  width `matching.corridor_width_meters = 1000` is buffered onto `trip_routes.corridor` at
  publish (needed in Phase 4 so Phase 5 can match). Stop proximity 500 m, default time window
  ±60 min, no detour. Recorded as BR-MATCH-02/03/05.

### OD-007 — Meaning of price in MVP

- **Question**: What does the displayed price mean when no payments exist? Is it computed by
  the formula only, or may drivers set/override? How is money exchanged?
- **Context**: MEP §32 gives 10 EGP + 3 EGP/km as a *concept*; §31 forbids payments without
  approval. Users will still hand over cash.
- **Options**: (a) formula price shown as "suggested contribution", cash off-platform,
  no override; (b) driver sets a per-seat price within bounds, formula shown as guidance;
  (c) hide prices entirely in MVP.
- **Recommendation**: (a) — deterministic, avoids price competition turning the community into a
  taxi market, keeps the pricing engine server-side and configurable.
- **Impact**: BR-TRIP-09, BR-PRICE-05, trip form and cards, landing copy.
- **Decision**: APPROVED (option a) by the product owner on 2026-10-02. The server-computed
  amount is a **suggested contribution**, paid in cash off-platform. Drivers cannot override it.
  No payments, wallets or payouts (BR-PRICE-06). Recorded as BR-TRIP-09 and BR-PRICE-05.

### OD-008 — Cancellation windows and consequences

- **Question**: Are there time windows after which cancelling has consequences, and what are
  they (warning, visible cancellation count, temporary block)?
- **Options**: (a) record only, show "cancellations in last 90 days" on profile; (b) (a) +
  automatic warning after N late cancellations; (c) (b) + temporary suspension.
- **Recommendation**: (a) for MVP; the data model already records timing so (b)/(c) can be
  applied later. Late = < 2 h before departure.
- **Impact**: BR-JOIN-10, profile UI, trust indicators.
- **Decision**: APPROVED (option a) by the product owner on 2026-10-15. Every cancellation stores
  actor, timestamp and `minutes_before_departure_at_cancel`. Late means fewer than
  `bookings.late_cancel_minutes` (120) before departure. Public profiles show
  `cancellationsLast90Days` (`bookings.cancellation_window_days` = 90): passenger-cancelled
  join requests plus trips the user cancelled as driver. No automatic warning or suspension.

### OD-009 — Sensitive document retention

- **Question**: How long are identity/licence/vehicle documents kept after a decision?
- **Options**: delete immediately on approval (keep decision only); 30 days; 90 days; keep while
  account active.
- **Recommendation**: 30 days after decision for approved and rejected documents, then purge;
  decision record and reviewer kept indefinitely. Legal counsel should confirm against Egyptian
  data-protection law (PDPL 151/2020).
- **Impact**: `stored_files.purge_after`, purge job, privacy policy text.
- **Decision**: APPROVED (30 days) by the product owner on 2026-10-02. Configuration key
  `verification.document_retention_days = 30`. Object bytes are deleted; the decision row and
  reviewer identity stay. Legal counsel still reviews the privacy notice before public launch
  (R-14). Recorded as BR-VER-06.

### OD-010 — Moderation policy

- **Question**: Which report reasons lead to which actions; strike thresholds; auto-hide rules.
- **Recommendation**: manual review for all reports in MVP; auto-hide a message after 3
  independent reports pending review; suspension always manual.
- **Impact**: BR-SAFE-03, admin workflow, chat behaviour.

### OD-011 — Phone number sharing after acceptance

- **Question**: When a request is accepted, do driver and passenger see each other's phone
  numbers, or is in-app chat the only channel?
- **Options**: (a) chat only; (b) reveal on acceptance; (c) per-user opt-in to reveal.
- **Recommendation**: (c) default off — privacy by default, but respects that many users will
  want to call on the day.
- **Impact**: BR-CHAT-07, trip detail UI, `user_profiles` preference column.

### OD-012 — Maximum passenger seats per trip

- **Question**: Hard cap for `total_seats` (`trips.max_passenger_seats`)?
- **Recommendation**: 7 (covers vans/minibuses) while still bounded by `vehicle.seat_capacity − 1`.
- **Impact**: BR-TRIP-02, forms.
- **Decision**: APPROVED (7) by the product owner on 2026-10-02. Configuration key
  `trips.max_passenger_seats = 7`. Still bounded by `vehicle.seat_capacity − 1`. Recorded as
  BR-TRIP-02.

### OD-013 — Dual-mode accounts in UI

- **Question**: Can one account act as passenger and driver, switching modes in the UI?
- **Recommendation**: Yes; the driver area (`/drive`) is available once `DRIVER` is held.
  Backend already supports both roles on one user.
- **Impact**: navigation, onboarding, landing copy.
- **Decision**: APPROVED by the product owner on 2026-10-01. Recorded as BR-ACC-04.

### OD-014 — Pending join-request expiry

- **Question**: When does an unanswered `PENDING` request expire?
- **Options**: at departure time; N hours after creation; whichever first.
- **Recommendation**: at `departure_at` (a request for a trip that has departed is moot) and
  the driver is reminded 24 h and 2 h before departure of unanswered requests.
- **Impact**: BR-JOIN-09, expiry job, notifications.
- **Decision**: APPROVED by the product owner on 2026-10-15. A pending request expires at
  `trips.departure_at` via an idempotent worker job. The 24 h and 2 h driver reminders are
  notification events and ship with Phase 7.

### OD-015 — Community chat in MVP

- **Question**: Ship the general community area (announcements/help) in Phase 7 or defer?
- **Recommendation**: Defer to after launch; ship an admin-authored **announcements** feed (read
  only) instead to preserve the community feel with zero moderation load.
- **Impact**: Phase 7 scope, `conversations.type` enum.

### OD-016 — Rating dimensions and visibility

- **Question**: Overall only or also punctuality/communication/experience? Are comments public?
  Minimum ratings before a public average?
- **Recommendation**: overall (required) + the three dimensions (optional); comments visible
  to the ratee and admins only; show average after ≥ 3 ratings.
- **Impact**: `ratings` columns, profile UI, BR-RATE-03.

### OD-017 — Trip start/complete semantics

- **Question**: Does the driver press Start/Complete, or does the system transition automatically?
- **Recommendation**: Driver-initiated Start allowed from 30 min before `departure_at`;
  driver-initiated Complete; system auto-completes `IN_PROGRESS` trips at
  `estimated_arrival_at + 6 h` and auto-expires `PUBLISHED` trips not started by
  `departure_at + 60 min`. Ratings open on `COMPLETED`.
- **Impact**: BR-TRIP transitions, jobs, rating availability.
- **Decision**: APPROVED (recommended) by the product owner on 2026-10-02. Driver Start is
  allowed from `trips.start_window_minutes = 30` before `departure_at`. Driver Complete is
  manual. The worker auto-completes `IN_PROGRESS` at `estimated_arrival_at +
  trips.auto_complete_hours` (6) and expires `PUBLISHED`/`FULL` not started by
  `departure_at + trips.expire_grace_minutes` (60). Ratings remain Phase 8.

### OD-018 — Recurring trips — DEFERRED

Not in the master prompt. Commuters will want "every weekday 08:00". Revisit after launch
metrics; design note: a `trip_templates` table generating trips N days ahead.

### OD-019 — Transactional email provider

- **Question**: Which SMTP/email API for verification, reset and notifications?
- **Recommendation**: any SMTP-compatible provider behind an `EmailSender` protocol; Mailpit in
  dev. Vendor choice needs approval (cost, deliverability in Egypt).
- **Impact**: Phase 2 email verification, Phase 7 notifications.
- **Decision**: APPROVED by the product owner on 2026-10-01 for the *abstraction*: all sending
  goes through an `EmailSender` protocol with an SMTP implementation, Mailpit in development.
  Selecting and paying for a production provider remains a separate approval before Phase 12
  (`email.from_address`, `email.from_name` are configuration).

### OD-020 — Account deletion policy

- **Question**: Can users self-delete? What blocks deletion (active trips, accepted requests)?
  What is retained (ratings, messages, audit)? Legal retention?
- **Recommendation**: self-service delete allowed when no `PUBLISHED`/`FULL`/`IN_PROGRESS`
  trips and no `ACCEPTED` requests; anonymise per `database.md` §7; keep audit logs; 14-day
  grace period before anonymisation with login cancelling it. Legal review recommended.
- **Impact**: `DELETE /me`, jobs, privacy policy.
- **Decision**: APPROVED by the product owner on 2026-10-01. Recorded as BR-ACC-07 with
  `accounts.deletion_grace_days = 14`. Legal review of the privacy policy wording is still
  outstanding and is tracked for Phase 12.

### OD-021 — Minimum age and legal acceptance

- **Recommendation**: 18+, explicit acceptance of terms/privacy at registration with versioned
  documents. Requires legal confirmation.
- **Decision**: APPROVED by the product owner on 2026-10-01. Recorded as BR-ACC-08 with
  `accounts.minimum_age_years = 18`, `legal.terms_version` and `legal.privacy_version`; the
  accepted versions and timestamp are stored on the user row. The legal documents themselves are
  still to be drafted (Phase 12).

### OD-022 — Licence plate visibility

- **Options**: never shown; shown to accepted passengers only; public.
- **Recommendation**: accepted passengers only (helps identify the car on pickup day).
- **Decision**: APPROVED (accepted passengers only) by the product owner on 2026-10-02. The
  owner and `ADMIN` may always see the plate. Search, public profiles and anyone who is not an
  accepted party of the trip never see it. Recorded as BR-VEH-02; trip-party disclosure is
  enforced when join requests land in Phase 6.

### OD-023 — Trip editing after acceptances

- **Options**: lock all fields; allow notes/seat increases only; allow everything with
  passenger notification and passenger right to cancel without consequence.
- **Recommendation**: allow notes and seat increase freely; changing departure time by > 15 min
  or changing route requires cancelling and republishing.
- **Decision**: APPROVED (recommended) by the product owner on 2026-10-02. After at least one
  `ACCEPTED` request: notes and increasing `total_seats` are free; a departure shift of more
  than `trips.edit_departure_tolerance_minutes` (15) or a route/stop change is rejected
  (`INVALID_TRANSITION`) — cancel and republish instead. With no acceptances, BR-TRIP-07 still
  applies (all fields, seats cannot drop below reserved). Recorded as BR-TRIP-07.

### OD-024 — Required vehicle documents

- **Recommendation**: vehicle registration (licence) front + back; vehicle photo optional.
  Insurance not required in MVP.
- **Decision**: APPROVED (recommended option) by the product owner on 2026-10-02. Required
  types: `REGISTRATION_FRONT`, `REGISTRATION_BACK`. Optional: `VEHICLE_PHOTO`. Insurance is not
  collected. Recorded as BR-VER-02 and BR-VEH-01; configuration key
  `vehicles.required_document_types`.

### OD-025 — AI provider and behaviour policy

- **Question**: LLM vendor, data-processing agreement, Arabic quality, what the assistant may
  say (tone, refusals), disclosure to users.
- **Recommendation**: vendor with strong Arabic and function-calling; no user PII sent; visible
  "AI assistant" label and disclaimer; refusals for anything outside trips/help.
- **Impact**: Phase 10 entirely.

### OD-026 — Production hosting provider

- **Recommendation**: managed PostgreSQL + a managed container service or a single hardened
  Docker host with Caddy in a region with low latency to Egypt (e.g. EU-south/Middle East).
  Cost and data-residency need approval.

### OD-027 — Domain name

Needed for cookies, CORS, emails, OG metadata. Reference docs use `fisikkati.app` as placeholder.

### OD-028 — Multi-community scoping — DEFERRED

MVP is one community (El Obour and surroundings). Schema keeps a path to a `communities`
table later; no code now.

### OD-029 — Search/trip visibility for unauthenticated visitors

- **Options**: fully private (login required to search); public search with blurred results
  and login to request; public trip pages for SEO.
- **Recommendation**: login required to search and view trips in MVP (privacy of a small
  community); public pages remain informational. Revisit for growth.
- **Impact**: permission matrix rows, SEO scope, rate limits.
- **Decision**: APPROVED (login required) by the product owner on 2026-10-02. Search and trip
  detail require a session. Public marketing pages stay informational. Recorded as BR-MATCH-09.

### OD-030 — Product analytics tooling and consent

- **Recommendation**: first-party `analytics_events` only (no third-party script) in MVP;
  consent banner not required for first-party, non-identifying events, but confirm with legal.

### OD-031 — Brand wordmark vs product name

- **Question**: The supplied logo contains the Arabic wordmark **«فالسكة عبور»**, while the
  product name used across the documentation and the UI is **«في سكتي» / "Fi Sikkati"**. Which
  one is the public brand name?
- **Context**: The logo artwork and its colour (`#CCF618`) were approved for use, and the icon
  set, palette and Open Graph card are now generated from it. The UI currently shows the logo
  mark next to the wordmark «في سكتي» as live text, so renaming is a copy change, not a redesign.
- **Options**: (a) keep «في سكتي» as the product name and treat the artwork as a mark only;
  (b) rename the product to «فالسكة» (and adjust the repository/product docs);
  (c) regenerate the logo artwork with the «في سكتي» wordmark.
- **Recommendation**: (a) for now — it is reversible and blocks nothing; decide before the first
  public release because it affects the domain name (OD-027), app store listing and all copy.
- **Impact**: `messages/*.json` (`Common.brand`, `Metadata.*`), logo artwork, domain, store
  listings, `docs/design-system.md`.
- **Decision**: APPROVED (option a) by the product owner on 2026-10-01 — «في سكتي» stays the
  product name and the supplied artwork is used as a mark only. Revisit before the first public
  release together with OD-027 (domain name).
