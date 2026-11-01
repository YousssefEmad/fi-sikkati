# Product Requirements Document — Fi Sikkati

| Field | Value |
| --- | --- |
| Version | 0.1 (Phase 0) |
| Source of truth | Master Engineering Prompt (MEP) §1–§101; open items in `open-decisions.md` |
| Related | `business-rules.md`, `permission-matrix.md`, `architecture.md`, `database.md`, `api.md` |

Requirement IDs (`FR-*`, `NFR-*`) are stable and are referenced from tests, ADRs and code comments.
Where a requirement depends on an unresolved decision it carries the `OD-xxx` reference.

---

## 1. Vision

Fi Sikkati ("on my way") is a community ride-sharing and **route-matching** platform.

A driver who is already planning to travel from A to B at a given time publishes that trip.
Passengers search for trips already going their way, request seats, and — once the driver
accepts — share the ride. Several passengers can share one trip up to the available seats.

Value proposition: **Find people already going your way.**

### 1.1 What this product is NOT

- Not ride-hailing: passengers never "order a car"; drivers never receive dispatch requests.
- Not a taxi marketplace: drivers are community members making trips they would make anyway.
- Not a payments platform in MVP: no money moves through the system until explicitly approved (OD-007).

### 1.2 Origin problem

Residents of El Obour City (Egypt) coordinate rides in a WhatsApp group with messages like
"leaving El Obour 8 AM to Nasr City". The group suffers from: buried messages, missed trips,
no search/filter by route or time, no seat management, no verification, no history, no
notifications, no reporting, no administration, no analytics, no business model.

### 1.3 Core flow (MEP §3)

```
DRIVER PUBLISHES TRIP → PASSENGERS DISCOVER TRIP → PASSENGER REQUESTS TO JOIN
→ DRIVER ACCEPTS / DECLINES → SEATS ARE RESERVED → BOTH COMMUNICATE
→ TRIP STARTS → TRIP COMPLETES → RATING / FEEDBACK
```

---

## 2. Users and roles

| Role | Description | Granted |
| --- | --- | --- |
| `PASSENGER` | Any registered user. Can search, request seats, chat on trips they joined, rate. | Automatically on registration |
| `DRIVER` | A user whose driver verification is `APPROVED`. Can register vehicles, publish trips, manage requests. | On driver-verification approval (Phase 3) |
| `ADMIN` | Platform operator. Full moderation, verification, configuration, analytics. | Manually by an existing admin (bootstrap via seed/CLI) |

- One account may hold both `PASSENGER` and `DRIVER` roles. The identity model is designed for
  this; whether the product exposes it in MVP is **OD-013** (recommendation: yes).
- Future roles (`MODERATOR`, `SUPPORT_AGENT`, `COMMUNITY_ADMIN`, `SUPER_ADMIN`) are **not**
  implemented. The RBAC design supports adding them without schema change (see `permission-matrix.md`).

### 2.1 Personas

| Persona | Need | Success |
| --- | --- | --- |
| **Salma, commuter passenger** (El Obour → Nasr City, weekdays 08:00) | Find a trusted driver leaving around 08:00 without scrolling WhatsApp | Finds a matching trip in <1 minute, gets accepted, knows pickup point |
| **Ahmed, commuter driver** (El Obour → Downtown, weekdays 07:30) | Fill 3 empty seats with verified neighbours, split fuel cost, no phone spam | Publishes trip in <2 minutes, accepts requests from phone, chats in one place |
| **Mona, occasional passenger** (weekend trip to 6th of October) | Discover whether anyone is going that way on Friday | Search by date returns compatible trips or a clear empty state |
| **Omar, community admin** | Keep the community safe: verify drivers, handle reports, suspend abusers | Verification queue and reports triaged from one dashboard with an audit trail |

---

## 3. Functional requirements

### 3.1 Accounts & authentication (Phase 2)

| ID | Requirement | Dependency |
| --- | --- | --- |
| FR-AUTH-01 | Users register with full name, password, phone number, and email; city/general location optional. Only required data is collected. | OD-004 **APPROVED**: email is the identifier; phone is optional and unverified |
| FR-AUTH-02 | Users log in and out; sessions use short-lived access tokens and rotating refresh sessions (ADR-0004). | — |
| FR-AUTH-03 | Users can request a password reset and set a new password via a single-use, expiring link. | OD-019 **APPROVED** (SMTP port; production vendor still a later approval) |
| FR-AUTH-04 | Users can view/edit their profile: display name, city, preferred language, bio, phone. Profile photo waits for the files module (Phase 3). | — |
| FR-AUTH-05 | Users can list and revoke their active sessions/devices. | — |
| FR-AUTH-06 | Account statuses: `ACTIVE`, `SUSPENDED`, `DEACTIVATED`, `DELETED`. Suspended/deactivated users cannot authenticate. | — |
| FR-AUTH-07 | Registration, login and reset endpoints are rate-limited and resistant to account enumeration. | — |
| FR-AUTH-08 | Account deletion workflow exists and follows the approved policy. | OD-020 **APPROVED** (BR-ACC-07) |

### 3.2 Identity verification (Phase 2 basic workflow, Phase 3 documents)

| ID | Requirement | Dependency |
| --- | --- | --- |
| FR-VER-01 | Users can submit identity verification (document type + private file upload). Status: `NOT_SUBMITTED`, `PENDING`, `APPROVED`, `REJECTED`. Status is stored on the account in Phase 2; document upload is Phase 3 (`files` + private bucket). | OD-002 **APPROVED**: required before the first join request |
| FR-VER-02 | Admins review pending submissions, approve or reject with a reason; user is notified. | — |
| FR-VER-03 | Identity documents are private: never public URLs, access is audited, retention is enforced. | OD-009 (retention period) |
| FR-VER-04 | Verified identity is shown as a badge; the underlying data is never shown to other users. | — |

### 3.3 Driver & vehicle (Phase 3)

| ID | Requirement | Dependency |
| --- | --- | --- |
| FR-DRV-01 | A user can apply to become a driver by submitting a driver verification (driving licence + required vehicle documents). | OD-003, OD-024 |
| FR-DRV-02 | Admin approval grants the `DRIVER` role; rejection records a reason; user is notified either way. | — |
| FR-DRV-03 | A driver can register one or more vehicles: make, model, year, colour, type, seat capacity, licence plate, status `ACTIVE`/`INACTIVE`. | Multiple vehicles: allowed by design; limit configurable (`vehicles.max_per_driver`) |
| FR-DRV-04 | Vehicle documents are stored privately and verified by admin (`PENDING`, `APPROVED`, `REJECTED`). | OD-024 |
| FR-DRV-05 | Public driver profile shows: display name, photo, verification badges, rating, completed-trip count, vehicle type/model/colour. Licence plate visibility follows the approved rule. | OD-022 |
| FR-DRV-06 | Only `APPROVED` vehicles with `ACTIVE` status can be attached to a published trip. | — |

### 3.4 Trips (Phase 4)

| ID | Requirement | Dependency |
| --- | --- | --- |
| FR-TRIP-01 | A driver creates a trip with: origin, destination, optional intermediate stops, departure date-time, estimated arrival, route geometry, total seats, available seats, price info, notes, vehicle. | OD-005 (route provider), OD-007 (price semantics) |
| FR-TRIP-02 | Trip statuses: `DRAFT`, `PUBLISHED`, `FULL`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `EXPIRED`. Transitions are defined in `business-rules.md` §3. | OD-017 (start/complete semantics) |
| FR-TRIP-03 | Drivers can edit trips; edit restrictions after passengers are accepted follow the approved rule. Accepted passengers are notified of edits. | OD-023 |
| FR-TRIP-04 | Drivers can cancel a trip with confirmation; all pending/accepted requests transition accordingly and passengers are notified. | OD-008 |
| FR-TRIP-05 | Trip detail page shows route on a map, stops, departure, seats left, price, driver card, vehicle summary. | — |
| FR-TRIP-06 | Trips whose departure time passes without starting are automatically `EXPIRED` by a background job. | Grace period configurable (`trips.expire_grace_minutes`) |
| FR-TRIP-07 | Driver dashboards list upcoming, active and past trips with request counts. | — |

### 3.5 Search & route matching (Phase 5)

| ID | Requirement | Dependency |
| --- | --- | --- |
| FR-SRCH-01 | Passengers search by pickup point, drop-off point, date and time window; results only include `PUBLISHED` trips with ≥ requested seats. | — |
| FR-SRCH-02 | Compatibility is computed from route geometry with PostGIS: pickup and drop-off must lie within the trip's route corridor, in route order. Exact-destination match and route compatibility are shown distinctly. | OD-006 thresholds |
| FR-SRCH-03 | Optional filters: verified driver only, minimum rating, vehicle type, price range. | — |
| FR-SRCH-04 | Ranking is deterministic and documented (`business-rules.md` §5): geographic fit → time fit → seats → status → filters. No undocumented ranking. | — |
| FR-SRCH-05 | Search results show approximate locations only; exact addresses are never exposed. | OD-001 |
| FR-SRCH-06 | Search is available to authenticated users; public (unauthenticated) visibility follows the approved rule. | OD-029 |
| FR-SRCH-07 | Results are paginated; empty state explains how to widen the search. | — |

### 3.6 Join requests & seats (Phase 6)

| ID | Requirement | Dependency |
| --- | --- | --- |
| FR-JOIN-01 | A passenger requests to join a trip with: seats requested, pickup point, drop-off point, optional note. Statuses: `PENDING`, `ACCEPTED`, `REJECTED`, `CANCELLED`, `EXPIRED`, `COMPLETED`. | — |
| FR-JOIN-02 | The driver accepts or rejects; acceptance atomically reserves seats. **Overbooking is impossible** under concurrency (DB lock + CHECK constraint, `business-rules.md` §4). | — |
| FR-JOIN-03 | A passenger can cancel a pending or accepted request (with confirmation); accepted-seat release is atomic. Consequences follow the cancellation policy. | OD-008 |
| FR-JOIN-04 | One passenger can have at most one active (`PENDING`/`ACCEPTED`) request per trip. Requests are idempotent via `Idempotency-Key`. | — |
| FR-JOIN-05 | Pending requests expire automatically per the approved rule. | OD-014 |
| FR-JOIN-06 | Drivers cannot request to join their own trips. | — |
| FR-JOIN-07 | When available seats reach 0 the trip becomes `FULL`; a release returns it to `PUBLISHED`. | — |

### 3.7 Communication (Phase 7)

| ID | Requirement | Dependency |
| --- | --- | --- |
| FR-CHAT-01 | Every trip has one conversation. Members: the driver and passengers with `ACCEPTED` requests. Text only. | — |
| FR-CHAT-02 | Messages have timestamps, sender, read state (per-member last-read pointer), delivery via WebSocket with HTTP fallback. | — |
| FR-CHAT-03 | System messages are posted for: passenger accepted, passenger cancelled, driver cancelled, trip updated, trip starting soon. | — |
| FR-CHAT-04 | Messages can be reported; membership ends when the request is cancelled/rejected (history retained read-only for the member's period). | — |
| FR-CHAT-05 | Whether phone numbers are shared after acceptance follows the approved rule. | OD-011 |
| FR-CHAT-06 | Community chat (announcements/help) is a separate conversation type with moderation, reporting, rate limiting and anti-spam. Inclusion in MVP: | OD-015 |

### 3.8 Notifications (Phase 7)

| ID | Requirement | Dependency |
| --- | --- | --- |
| FR-NOTIF-01 | Centralised notification service with channels `IN_APP` and `EMAIL` (push later; SMS only if approved — OD-004). | OD-019 |
| FR-NOTIF-02 | Events: request received, request accepted, request rejected, trip updated, trip cancelled, new message, trip starting soon, verification status changed, report update. | — |
| FR-NOTIF-03 | Users manage per-event, per-channel preferences; safety-critical notifications (trip cancelled) cannot be disabled in-app. | — |
| FR-NOTIF-04 | In-app notification centre with unread count, mark-as-read, pagination. | — |

### 3.9 Safety & trust (Phase 8)

| ID | Requirement | Dependency |
| --- | --- | --- |
| FR-SAFE-01 | After a `COMPLETED` trip, driver and each completed passenger may rate each other once. No self-rating, no rating before completion. | OD-016 (dimensions, visibility) |
| FR-SAFE-02 | Users can report a user, trip or message with a reason category and description. Statuses: `OPEN`, `UNDER_REVIEW`, `RESOLVED`, `DISMISSED`. | — |
| FR-SAFE-03 | Users can block other users; blocked users cannot see each other's trips, request each other's trips, or message each other. | — |
| FR-SAFE-04 | Verified-identity and verified-driver badges are shown on profiles and trip cards. | — |
| FR-SAFE-05 | Safety centre page: guidelines, how to report, how verification works. No claim of guaranteed physical safety. No emergency-services integration. | — |
| FR-SAFE-06 | Trust indicators shown: badges, completed trips, rating (after minimum count), account age. No composite "trust score". | OD-016 |
| FR-SAFE-07 | Audit log records every sensitive action (`security.md` §9). | — |

### 3.10 Administration (Phase 9)

| ID | Requirement |
| --- | --- |
| FR-ADM-01 | Users: search, filter, view, change verification status, suspend, deactivate, restore. |
| FR-ADM-02 | Drivers: verification queue, view documents (audited), approve/reject with reason, vehicles. |
| FR-ADM-03 | Trips: search, inspect, cancel with reason, view related reports. |
| FR-ADM-04 | Reports: queue by type, assign status, take moderation action (warn, suspend, remove content), resolve with notes. |
| FR-ADM-05 | Analytics: totals and time series for users, active users, drivers, trips, completed, cancellations, join requests, successful matches. |
| FR-ADM-06 | System: configuration values, feature flags, notification configuration. |
| FR-ADM-07 | Audit log viewer (read-only, filterable). |
| FR-ADM-08 | Every admin mutation requires server-side permission checks and writes an audit entry. |

### 3.11 AI assistant (Phase 10)

| ID | Requirement | Dependency |
| --- | --- | --- |
| FR-AI-01 | Natural-language trip discovery: free text → validated structured search parameters → deterministic search API. | OD-025 |
| FR-AI-02 | Help/FAQ assistant grounded in platform help content. | OD-025 |
| FR-AI-03 | AI is isolated in its own module, calls only whitelisted read-only tools, output is schema-validated, rate-limited and logged. AI never creates bookings, approves drivers, bypasses authorization or changes records. | — |
| FR-AI-04 | AI features are behind a server-side feature flag. | — |

### 3.12 Public site (Phase 1 shell, content Phase 4+)

| ID | Requirement |
| --- | --- |
| FR-PUB-01 | Landing page explains: what, why, how it works, for passengers, for drivers, safety, verification, community, FAQ, CTA. |
| FR-PUB-02 | Pages: how it works, safety, FAQ, about, contact, terms, privacy. |
| FR-PUB-03 | Public pages are SEO-ready: metadata, Open Graph, canonical URLs, sitemap, robots.txt, structured data. |
| FR-PUB-04 | Arabic and English, RTL/LTR, accessible language switch. |

---

## 4. User journeys

### 4.1 Passenger — first trip

1. Lands on the landing page (AR default for `ar` locale), understands "find people already going your way".
2. Registers (FR-AUTH-01) → onboarding: profile → verification (if required, OD-002) → explainer: search, request, chat, safety.
3. Searches El Obour → Nasr City, tomorrow 07:30–08:30 (FR-SRCH-01).
4. Sees results ranked by fit; each card shows approximate pickup, departure, seats left, price, driver badges and rating.
5. Opens trip details: route map, stops, driver card, vehicle summary.
6. Requests 1 seat with pickup/drop-off points and a note (FR-JOIN-01). Sees "Request sent — waiting for driver".
7. Receives notification "accepted" (FR-NOTIF-02); the trip appears under *Upcoming trips*; trip chat unlocks.
8. Chats to confirm pickup; receives "trip starting soon".
9. After completion, is prompted to rate the driver (FR-SAFE-01).

Failure paths: no results → empty state with suggestions; driver rejects → notification + suggestions for similar trips; driver cancels → notification, request `CANCELLED`, seats released.

### 4.2 Driver — first trip

1. Registers as a normal user, opens *Become a driver*.
2. Submits driver verification: driving licence + vehicle + vehicle documents (FR-DRV-01). Sees "Verification pending" empty state.
3. Admin approves → notification → `DRIVER` role granted.
4. Creates a trip: picks origin/destination on map, route preview, departure time, seats, price, notes; publishes (FR-TRIP-01).
5. Receives join requests; reviews passenger card (badges, rating, note, pickup point); accepts/rejects (FR-JOIN-02).
6. Trip becomes `FULL` when seats run out. Chat with accepted passengers.
7. Starts and completes the trip (semantics per OD-017); rates passengers.

### 4.3 Admin — verification and report handling

1. Logs in; dashboard shows pending verifications, open reports, key metrics.
2. Opens the verification queue; views documents via short-lived signed URL (access audited, FR-VER-03).
3. Approves or rejects with a reason; user notified; audit entry written.
4. Opens a report; inspects the trip/message/user; takes a moderation action (warn/suspend/remove); resolves with notes; audit entry written.

### 4.4 Cancellation journeys

- Passenger cancels accepted request → seats released atomically → driver notified → system message in chat.
- Driver cancels trip → all `PENDING` → `CANCELLED`, all `ACCEPTED` → `CANCELLED`; passengers notified; conversation frozen read-only.
- Consequences (cancellation history, limits) follow OD-008.

---

## 5. Screens (MEP §50)

| Area | Screens |
| --- | --- |
| Public | Landing, How it works, Safety, FAQ, About, Contact, Terms, Privacy |
| Auth | Login, Register, Verify (email/identity), Forgot password, Reset password |
| Passenger | Dashboard, Search, Results, Trip details, Join request, My trips (upcoming / completed), Notifications, Messages, Profile, Settings |
| Driver | Dashboard, Create trip, My trips, Trip details (with requests + passengers), Trip history, Vehicles, Verification, Messages, Notifications, Profile, Settings |
| Admin | Dashboard, Users, Drivers, Verification, Vehicles, Trips, Reports, Moderation, Analytics, System settings, Audit logs |

Every list screen has a designed empty state (MEP §79). Every destructive action has a
confirmation (MEP §82). Every async action has a loading and success/failure state (MEP §81).

---

## 6. Non-functional requirements

| ID | Requirement |
| --- | --- |
| NFR-01 | Arabic is first-class: RTL layout, translated validation and system messages, localised dates/numbers/currency (`next-intl`, ICU). |
| NFR-02 | Mobile-first responsive design; proper mobile interaction patterns (bottom navigation, sheets), not shrunken desktop. |
| NFR-03 | Accessibility: WCAG 2.2 AA target — semantic HTML, keyboard navigation, visible focus, labelled controls, accessible dialogs, error announcements. |
| NFR-04 | Performance: Server Components by default, minimal client JS, image optimisation, pagination everywhere, indexed queries; Core Web Vitals measured before optimising. |
| NFR-05 | Security: see `security.md`; no secrets in git; sensitive documents never public. |
| NFR-06 | Observability: request IDs, structured JSON logs, health checks, error tracking; no PII/tokens in logs. |
| NFR-07 | Scale: ~2,000 users initially; stateless API horizontally scalable; PostgreSQL is the source of truth; Redis for cache/rate-limit/jobs/pubsub only. |
| NFR-08 | Testability: unit, integration, API, DB, component, E2E; concurrency tests for seat reservation (`testing.md`). |
| NFR-09 | Data lifecycle: retention, deletion and anonymisation documented and enforced (OD-009, OD-020). |
| NFR-10 | API-first: the same versioned REST API serves web and a future mobile app; no business logic in the frontend. |
| NFR-11 | PWA readiness: installable, app-like on mobile; no fake offline for transactional features. |

---

## 7. Explicitly out of scope until approved

| Item | Gate |
| --- | --- |
| Payments, wallets, fees, subscriptions | OD-007 + explicit approval (MEP §31, §33) |
| SMS channel | OD-004 |
| Emergency-services integration | MEP §23 — never without approval |
| Recurring trips | OD-018 |
| Media in chat | MEP §18 — not initially |
| Elasticsearch/OpenSearch | MEP §34 — only with demonstrated need |
| Native mobile app | MEP §63 — after PWA |
| Future roles (MODERATOR, SUPPORT_AGENT, COMMUNITY_ADMIN, SUPER_ADMIN) | MEP §8 |
| Multi-community scoping | OD-028 |

---

## 8. Success metrics (product analytics, MEP §55)

Events: `registration_started`, `registration_completed`, `verification_submitted`, `trip_created`,
`trip_search`, `trip_viewed`, `join_request_created`, `join_request_accepted`, `trip_completed`,
`trip_cancelled`. Tooling/consent approach: OD-030.

Initial KPIs: weekly published trips, search→request conversion, request acceptance rate,
completed-trip rate, cancellation rate, time-to-first-accepted-request for new passengers.
