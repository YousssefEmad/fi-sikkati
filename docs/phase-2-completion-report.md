# Phase 2 completion report — Authentication & Identity

Date: 2026-10-02

## Scope delivered

Accounts, cookie sessions (ADR-0004), email verification, password reset/change, profile edit,
session list/revoke, and account close (BR-ACC-07). The web app registers, signs in, and manages
the account against the API through same-origin `/api/*` rewrites so `__Host-` cookies attach to
the web origin.

Approved open decisions consumed: OD-002, OD-004, OD-013, OD-019, OD-020, OD-021.

## Explicitly not in this phase

| Item | Why |
| --- | --- |
| Identity document upload (`NATIONAL_ID_FRONT` / `BACK` / `SELFIE`) | Needs the `files` module and private bucket; required before the first join request (Phase 6), implemented in Phase 3 |
| Profile photo | `user_profiles.photo_file_id` waits on `stored_files` (Phase 3) |
| Phone OTP | OD-004: email is the identifier; SMS needs a separate vendor approval |
| Blocking (`/me/blocks`) | Phase 8 |
| Admin review of identity submissions | Phase 3 / 9 |

The account already stores `identityVerificationStatus` (`NOT_SUBMITTED` by default) and the
profile page shows it. There is no upload path yet.

## Quality gate

Recorded in `docs/project-status.md` §Phase 2 gate. Automated checks: ruff, mypy, import-linter,
pytest (auth/users/audit), Alembic round-trip, OpenAPI export, `pnpm typecheck` / lint / Vitest,
Playwright auth + smoke (AR/EN, desktop/mobile, axe).

## How to try it locally

1. Infrastructure: `pnpm infra:up` (Postgres, Redis, MinIO, Mailpit).
2. API: `cd apps/api && python -m uv run alembic upgrade head && python -m uv run uvicorn app.main:create_app --factory --reload --port 8000`
3. Web: `pnpm dev` → http://localhost:3000/ar
4. Create an account. Open Mailpit at http://localhost:8025 for the confirmation link.
5. Sign-in works before the address is confirmed; the account page shows a reminder banner.
