# API Changelog

Consumer-facing changes to the HTTP API (`/api/v1`). Breaking changes are marked **BREAKING**
and follow the deprecation policy in `api.md` §Versioning. The authoritative contract is
`packages/types/openapi.json`, regenerated from the FastAPI app in CI.

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
