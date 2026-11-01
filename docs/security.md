# Security Architecture

Threat model summary: a community platform holding identity documents, phone numbers,
approximate home locations and travel plans of ~2,000 people. The highest-impact failures are
(1) leaking identity/vehicle documents, (2) account takeover, (3) exposing exact locations or
phone numbers to strangers, (4) privilege escalation to admin, (5) abuse (spam, harassment,
fake trips). Controls below map to MEP §9, §22, §38, §39, §73, §74.

## 1. Authentication (ADR-0004)

| Control | Design |
| --- | --- |
| Password hashing | Argon2id (`argon2-cffi`), parameters tuned to ~250 ms on production hardware; peppered with a server-side secret via HMAC before hashing |
| Password policy | min length `auth.password_min_length` (10), max 128, checked against a breached-password list (offline k-anonymity range check, Phase 11) ; no composition rules |
| Access token | JWT (EdDSA/Ed25519), TTL 15 min, claims: `sub`, `sid`, `roles`, `iat`, `exp`, `jti`; keys rotated via `kid` |
| Refresh session | opaque 256-bit random, stored as SHA-256 hash in `auth_sessions`, TTL 30 days, **rotated on every use**; reuse of a rotated token revokes the whole `family_id` (theft detection) |
| Web transport | `__Host-fs_access` and `__Host-fs_refresh` cookies: `HttpOnly; Secure; SameSite=Lax; Path=/`; refresh cookie scoped to `/api/v1/auth/refresh` |
| Non-browser clients | `Authorization: Bearer` + refresh in body; no cookies |
| CSRF | for cookie-authenticated mutations: `Origin`/`Sec-Fetch-Site` check + double-submit `X-CSRF-Token` bound to session; state-changing routes reject `GET`; `SameSite=Lax` as defence in depth |
| Logout | revokes session server-side; clears cookies |
| Session listing | users see and revoke devices (FR-AUTH-05) |
| Account enumeration | register/forgot-password respond identically whether or not the identifier exists; timing normalised; login error is generic |
| Brute force | rate limits §7 + progressive delay per identifier; lockout is *not* used (DoS vector) |
| Email verification | single-use hashed token, 24 h TTL; unverified accounts may sign in and manage their profile but cannot publish trips or request seats (BR-AUTH-05) |

## 2. Authorization

Deny-by-default RBAC, permissions in code (ADR-0005), enforced by FastAPI dependencies and
service-layer ownership checks (`permission-matrix.md` §3). Admin is never inferred from a
client claim alone: roles in the JWT are a hint; sensitive admin routes re-read roles from the
database. WebSocket subscriptions re-check membership.

## 3. Sensitive documents (ADR-0013)

| Control | Design |
| --- | --- |
| Storage | S3-compatible bucket `private-documents`, block-all-public-access, server-side encryption (SSE-S3 or KMS where available), versioning off, lifecycle rule as backup for the purge job |
| Keys | `documents/<owner-uuid>/<uuid7>.<ext>` — no user input in keys |
| Access | only through `GET /admin/verifications/…/download-url` → presigned GET, TTL 120 s, `Content-Disposition: attachment`; every issuance writes `DOCUMENT_VIEWED` to `audit_logs` |
| Users' own documents | never downloadable; metadata only |
| Upload validation | size ≤ 10 MiB; extension allow-list `jpg jpeg png pdf`; MIME sniffed from bytes (`python-magic`), must agree with extension; images re-encoded (strips EXIF/GPS, defuses polyglots); PDFs checked for JavaScript/embedded files and rejected if present; AV scan (ClamAV sidecar) where infrastructure allows — recorded in `stored_files.scan_status` |
| Retention | `purge_after` set on decision to now + `verification.document_retention_days` (30, OD-009 approved); nightly purge job deletes the object and sets `purged_at` |
| Never | in PostgreSQL, in logs, in public bucket, in error messages, in analytics |

Profile photos go to `public-media` after the same validation + re-encoding + resizing.

## 4. Privacy (MEP §22)

| Data | Exposure rule |
| --- | --- |
| National ID number / documents | never exposed to any user; admin only via §3 |
| Phone number | never public; shared between driver and accepted passenger only if ⛔ OD-011 approves |
| Exact stop coordinates | accepted parties only (BR-TRIP-10); public/search sees points blurred by `privacy.location_blur_meters` (⛔ OD-001), computed server-side with deterministic per-trip jitter (not re-randomised per request, which would allow averaging) |
| Home address | never stored as such; users pick pickup points, which are still blurred for non-parties |
| Email | never public |
| Full legal name | private; `display_name` is public |
| Licence plate | owner + ADMIN + accepted trip parties only (OD-022 approved; BR-VEH-02) |
| Moderation data, reports, strikes | never shown to other users |

Users are informed in the privacy policy page (FR-PUB-02) how data is used; the analytics event
list is fixed (PRD §8) and contains ids only.

## 5. Input/output validation

Pydantic strict models for every request and response (unknown fields rejected on input,
response models prevent over-exposure). Zod on the client for UX. Query parameters typed.
Uploads validated per §3. GeoJSON/coordinates range-checked. Text fields length-limited and
Unicode-normalised (NFC); HTML never rendered from user content (React escapes by default; no
`dangerouslySetInnerHTML` for user text).

## 6. Web security headers & transport

TLS only (HSTS `max-age=63072000; includeSubDomains; preload`). Headers set by the API and by
Next.js middleware: `Content-Security-Policy` (nonce-based scripts, `frame-ancestors 'none'`,
explicit map/tile/API origins), `X-Content-Type-Options: nosniff`, `Referrer-Policy:
strict-origin-when-cross-origin`, `Permissions-Policy` (geolocation allowed on own origin only),
`Cross-Origin-Opener-Policy: same-origin`. CORS: allow-list of web origins, credentials allowed,
no wildcard.

## 7. Rate limiting (Redis sliding window)

| Endpoint | Limit (default; configurable) |
| --- | --- |
| `POST /auth/login` | 10 / 15 min per IP; 5 / 15 min per identifier |
| `POST /auth/register` | 5 / hour per IP |
| `POST /auth/password/forgot` | 3 / hour per identifier; 10 / hour per IP |
| verification uploads | 20 / day per user |
| `POST …/messages` | 30 / min per user (`chat.rate_limit_per_minute`) |
| `POST /reports` | 10 / day per user |
| `GET /search/trips` | 60 / min per user |
| `POST /ai/assistant` | 30 / hour per user |
| `POST /trips/{id}/join-requests` | 20 / hour per user |
| global | 600 / min per user, 300 / min per IP anonymous |

Responses: `429 RATE_LIMITED` + `Retry-After`. Limits are keyed on hashed identifiers.

## 8. Injection, SSRF, misc.

- SQL: SQLAlchemy Core/ORM with bound parameters only; raw SQL (PostGIS) uses `text()` with
  bound params; `sqlfluff`/review for any raw SQL.
- SSRF: the only outbound HTTP is to configured providers (maps, email, LLM, storage) via a
  client with allow-listed hosts, no redirects to other hosts, private IP ranges blocked.
- Path traversal: object keys are generated; file names from clients are display-only.
- Deserialisation: JSON only; no pickle; `jsonb` payloads schema-validated on read.
- Dependency hygiene: `uv lock`/`pnpm-lock.yaml` committed; Dependabot/Renovate; `pip-audit` and
  `pnpm audit` in CI; container images scanned (Trivy) in CI.
- Secrets: environment variables only; `.env` git-ignored; `.env.example` documents keys without
  values; `gitleaks` pre-commit and CI; production secrets in the platform's secret store
  (⛔ OD-026).
- Timing-safe comparisons for tokens (`hmac.compare_digest`).
- Clock skew: JWT `leeway` 30 s.

## 9. Audit log (MEP §28)

Append-only `audit_logs` (`database.md` §2.9). Actions (`action` values):

`AUTH_LOGIN_SUCCESS`, `AUTH_LOGIN_FAILED` (identifier hashed), `AUTH_LOGOUT`,
`AUTH_SESSION_REVOKED`, `AUTH_REFRESH_REUSE_DETECTED`, `AUTH_PASSWORD_RESET`,
`VERIFICATION_SUBMITTED`, `VERIFICATION_APPROVED`, `VERIFICATION_REJECTED`, `DRIVER_REVOKED`,
`DOCUMENT_UPLOADED`, `DOCUMENT_VIEWED`, `DOCUMENT_PURGED`,
`ROLE_GRANTED`, `ROLE_REVOKED`, `USER_SUSPENDED`, `USER_RESTORED`, `USER_DEACTIVATED`,
`USER_ANONYMISED`, `TRIP_CANCELLED_BY_ADMIN`, `TRIP_EXPIRED`, `REQUEST_EXPIRED`,
`REPORT_STATUS_CHANGED`, `MODERATION_ACTION`, `MESSAGE_REMOVED`, `SETTINGS_CHANGED`,
`FEATURE_FLAG_CHANGED`, `ADMIN_PII_VIEWED`.

Each entry: actor, target, request id, hashed IP, metadata without PII. Written in the same DB
transaction as the audited change so they cannot diverge. Application DB role cannot update or
delete rows.

## 10. Logging hygiene (MEP §39, §72)

`structlog` processor pipeline includes a scrubber that drops/masks keys matching
`password|token|secret|authorization|cookie|national_id|phone|email|document` and truncates
bodies. Request logs record method, path template (not raw path with ids where sensitive), status,
duration, `request_id`, `user_id` (hashed in production). Never log request bodies of auth,
verification or upload routes.

## 11. AI boundaries (MEP §29–§30)

- LLM sees: the user's message, non-PII trip summaries returned by tools, help content.
- LLM never sees: documents, phone numbers, emails, exact coordinates of other users.
- Tools are read-only and run as the requesting user; tool arguments are validated with strict
  Pydantic schemas before execution; outputs are validated before being returned to the client.
- Prompt-injection mitigations: tool results are wrapped as data, system prompt forbids
  following instructions inside data, output must match schema or the request is refused.
- Feature flag `ai.enabled` server-side; per-user rate limit; all interactions logged
  (`ai_interactions`) with hashed prompt for abuse review.

## 12. Security testing (see `testing.md` §6)

Authz matrix tests per endpoint; negative tests for IDOR (other users' trips/requests/
documents); upload fuzzing (wrong MIME, polyglot, oversize, traversal names); CSRF tests;
rate-limit tests; refresh-token reuse detection test; dependency and container scanning in CI;
a manual security review checklist at the end of every phase; external penetration test before
Phase 12 (recommended, ⛔ budget decision noted in `risk-register.md`).
