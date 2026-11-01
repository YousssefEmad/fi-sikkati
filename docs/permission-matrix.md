# Permission Matrix

Role-based access control for Fi Sikkati. **Every protected endpoint enforces these rules
server-side**; frontend role checks are for UX only (MEP §27).

## 1. Model

- **Roles** are static enums defined in code: `PASSENGER`, `DRIVER`, `ADMIN`. A user holds a
  set of roles (`user_roles` table).
- **Permissions** are static string constants defined in code (`<domain>:<action>`), grouped per
  role in a single mapping module (`apps/api/app/core/authz/permissions.py`). They are **not**
  stored in the database (ADR-0005): permissions are part of the application's behaviour and
  must be reviewed/versioned with code; storing them in a table would allow privilege changes
  without code review.
- **Ownership / relationship checks** ("is this my trip?", "am I a member of this conversation?")
  are enforced in the service layer in addition to the permission check. The matrix marks these
  with `own` / `member` / `party`.
- **Account status** gate: any request from a non-`ACTIVE` account is rejected with
  `ACCOUNT_INACTIVE` before permission evaluation.
- Adding a future role means adding an enum value and a permission set; no schema change.

## 2. Matrix

Legend: ✅ allowed · `own` only for resources the user owns/created · `member` only as a
conversation member · `party` only as driver or accepted passenger of that trip · ❌ denied ·
🔒 additionally audited.

### 2.1 Account & profile

| Permission | Anonymous | PASSENGER | DRIVER | ADMIN |
| --- | --- | --- | --- | --- |
| `auth:register` | ✅ | ❌ | ❌ | ❌ |
| `auth:login` / `auth:refresh` / `auth:logout` | ✅ / ❌ / ❌ | ✅ | ✅ | ✅ |
| `auth:password_reset` | ✅ | ✅ | ✅ | ✅ |
| `me:read` / `me:update` | ❌ | ✅ | ✅ | ✅ |
| `me:sessions:list` / `me:sessions:revoke` | ❌ | ✅ | ✅ | ✅ |
| `me:delete` | ❌ | ✅ (BR-ACC-07) | ✅ | ✅ |
| `users:read_public_profile` | ❌ | ✅ | ✅ | ✅ |

### 2.2 Verification

| Permission | PASSENGER | DRIVER | ADMIN |
| --- | --- | --- | --- |
| `verification:identity:submit` | ✅ own | ✅ own | ✅ own |
| `verification:identity:read` | ✅ own (status + metadata, never file) | ✅ own | ✅ 🔒 |
| `verification:driver:submit` | ✅ own | ✅ own (resubmit) | ✅ own |
| `verification:driver:read` | ✅ own | ✅ own | ✅ 🔒 |
| `verification:document:download` | ❌ | ❌ | ✅ 🔒 (signed URL) |
| `verification:review` (approve/reject) | ❌ | ❌ | ✅ 🔒 |

Users never download their own uploaded documents through the API (no need; reduces exposure).
They see file name, type, size, status.

### 2.3 Vehicles

| Permission | PASSENGER | DRIVER | ADMIN |
| --- | --- | --- | --- |
| `vehicles:create` | ✅ own (as part of driver application) | ✅ own | ❌ |
| `vehicles:read` | ✅ own | ✅ own | ✅ |
| `vehicles:update` / `vehicles:deactivate` | ✅ own | ✅ own | ✅ 🔒 |
| `vehicles:document:upload` | ✅ own | ✅ own | ❌ |
| `vehicles:review` | ❌ | ❌ | ✅ 🔒 |

`PASSENGER` may create a vehicle because vehicle registration is part of *applying* to become a
driver (BR-VER-02); the vehicle cannot be used on a trip until the owner holds `DRIVER` and the
vehicle is `APPROVED` (BR-TRIP-01, FR-DRV-06).

### 2.4 Trips

| Permission | Anonymous | PASSENGER | DRIVER | ADMIN |
| --- | --- | --- | --- | --- |
| `trips:create` | ❌ | ❌ | ✅ | ❌ |
| `trips:read` (detail, privacy-filtered) | ❌ | ✅ | ✅ | ✅ |
| `trips:read_exact_stops` | ❌ | `party` | `own` / `party` | ✅ |
| `trips:update` | ❌ | ❌ | ✅ own | ❌ |
| `trips:publish` / `trips:start` / `trips:complete` | ❌ | ❌ | ✅ own | ❌ |
| `trips:cancel` | ❌ | ❌ | ✅ own | ✅ 🔒 (reason) |
| `trips:list_own` | ❌ | ✅ (`role=passenger`) | ✅ | — |
| `trips:list_any` (admin search) | ❌ | ❌ | ❌ | ✅ |

### 2.5 Search

| Permission | Anonymous | PASSENGER | DRIVER | ADMIN |
| --- | --- | --- | --- | --- |
| `search:trips` | ❌ | ✅ | ✅ | ✅ |

### 2.6 Join requests

| Permission | PASSENGER | DRIVER | ADMIN |
| --- | --- | --- | --- |
| `join_requests:create` | ✅ (not on own trip) | ✅ (as passenger, not own trip) | ❌ |
| `join_requests:read` | ✅ own | ✅ own or on own trip | ✅ |
| `join_requests:cancel` | ✅ own | ✅ own | ❌ |
| `join_requests:accept` / `join_requests:reject` | ❌ | ✅ on own trip | ❌ |
| `join_requests:list_for_trip` | ❌ | ✅ own trip | ✅ |
| `join_requests:list_mine` | ✅ | ✅ | — |

### 2.7 Chat

| Permission | PASSENGER | DRIVER | ADMIN |
| --- | --- | --- | --- |
| `conversations:list_mine` | ✅ | ✅ | — |
| `conversations:read` / `messages:list` | `member` | `member` | ✅ 🔒 (moderation view only) |
| `messages:send` | active `member` | active `member` | ❌ |
| `messages:mark_read` | `member` | `member` | ❌ |
| `messages:report` | `member` | `member` | ❌ |
| `messages:remove` (moderation) | ❌ | ❌ | ✅ 🔒 |
| `community:*` | ⛔ OD-015 | ⛔ OD-015 | ⛔ OD-015 |

### 2.8 Notifications

| Permission | PASSENGER | DRIVER | ADMIN |
| --- | --- | --- | --- |
| `notifications:list` / `notifications:mark_read` | ✅ own | ✅ own | ✅ own |
| `notifications:preferences:read` / `update` | ✅ own | ✅ own | ✅ own |

### 2.9 Safety & trust

| Permission | PASSENGER | DRIVER | ADMIN |
| --- | --- | --- | --- |
| `ratings:create` | `party` of `COMPLETED` trip | `party` | ❌ |
| `ratings:read_summary` | ✅ | ✅ | ✅ |
| `reports:create` | ✅ | ✅ | ✅ |
| `reports:read` | ✅ own | ✅ own | ✅ |
| `reports:review` (status, resolution) | ❌ | ❌ | ✅ 🔒 |
| `blocks:create` / `blocks:delete` / `blocks:list` | ✅ own | ✅ own | ✅ own |
| `moderation:action` | ❌ | ❌ | ✅ 🔒 |

### 2.10 Administration

| Permission | ADMIN |
| --- | --- |
| `admin:users:read` / `admin:users:search` | ✅ 🔒 (PII view) |
| `admin:users:suspend` / `restore` / `deactivate` | ✅ 🔒 |
| `admin:roles:grant` / `admin:roles:revoke` | ✅ 🔒 |
| `admin:analytics:read` | ✅ |
| `admin:settings:read` / `admin:settings:update` | ✅ 🔒 |
| `admin:feature_flags:read` / `update` | ✅ 🔒 |
| `admin:audit:read` | ✅ |

All non-admin roles: ❌ for every `admin:*` permission.

### 2.11 AI

| Permission | PASSENGER | DRIVER | ADMIN |
| --- | --- | --- | --- |
| `ai:assistant:query` | ✅ (flag `ai.enabled`, rate-limited) | ✅ | ✅ |

The AI module itself holds no permissions: tools it calls run **as the requesting user** through
the same service layer, so it can never read or do more than that user could (MEP §29–§30).

### 2.12 System / jobs

Background workers use an internal service identity (`SYSTEM`) that is not a user and cannot be
authenticated over HTTP. It may: expire trips, expire requests, transition requests on trip
completion, send notifications, purge expired documents. Every system transition is written to
`audit_logs` with `actor_type = SYSTEM`.

## 3. Enforcement rules

1. Authentication dependency resolves the user and rejects non-`ACTIVE` accounts.
2. `require_permission(<perm>)` dependency on every non-public route; missing permission → `403 FORBIDDEN`.
3. Ownership/membership checks in the service layer → `404 NOT_FOUND` for resources the user
   may not know exist (trips of blocked users, other users' requests), `403` when existence is
   already known to the user.
4. Admin mutations additionally require a `reason` where marked and always write an audit entry
   in the same transaction as the change.
5. WebSocket connections authenticate on connect and re-check membership on every subscription.
6. Tests in `apps/api/tests/authz/` assert this matrix row by row (see `testing.md` §4).
