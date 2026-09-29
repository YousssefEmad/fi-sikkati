# ADR-0004 — Authentication: short-lived JWT access + rotating opaque refresh sessions, cookie transport for web

**Status**: Accepted · **Date**: 2026-09-29

## Context

MEP §5 requires short-lived access tokens, refresh/session rotation and a secure cookie
strategy. The same API must serve the Next.js web app today and a mobile app later (§63).
Server Components need to call the API on behalf of the user during SSR.

## Decision

- **Access token**: JWT signed with Ed25519 (`kid` for rotation), TTL 15 min, claims
  `sub, sid, roles, jti, iat, exp`. Stateless verification on every request; roles in the token
  are a hint — admin routes re-read roles from the DB.
- **Refresh session**: opaque 256-bit token, SHA-256 hash stored in `auth_sessions` with a
  `family_id`. Every refresh rotates the token; presenting an already-rotated token revokes the
  whole family (theft detection). TTL 30 days sliding, absolute max 90 days.
- **Web transport**: API sets `__Host-fs_access` and `__Host-fs_refresh` cookies
  (`HttpOnly; Secure; SameSite=Lax`), the refresh cookie path-scoped to the refresh endpoint.
  Cookie-authenticated mutations require `X-CSRF-Token` (double submit bound to `sid`) plus
  `Origin` verification. The web app and API share a registrable domain via the reverse proxy.
- **Non-browser clients**: `Authorization: Bearer` + refresh token in the response body.
- **Logout** revokes the session row; **password change/reset** revokes all sessions.
- Passwords: Argon2id with server pepper (`security.md` §1).

## Alternatives

- Server-side opaque sessions only (no JWT): one DB/Redis lookup per request; simpler
  revocation. Rejected because SSR + WebSocket + mobile benefit from stateless verification and
  15-minute exposure is acceptable with family revocation.
- Long-lived JWT without refresh: no revocation; rejected.
- Third-party auth provider: vendor lock-in and cost; the prompt did not approve a vendor.

## Consequences

- Revocation latency ≤ 15 min for access tokens except where routes re-check the DB (admin,
  sensitive). Suspension additionally deletes sessions so refresh fails immediately.
- Requires same-site deployment for `__Host-` cookies (deployment.md §8).
