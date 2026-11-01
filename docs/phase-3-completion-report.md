# Phase 3 completion report — Driver & Vehicle

Date: 2026-10-02

## Scope delivered

Private file storage (ADR-0013), identity document upload/review, driver application (licence +
vehicle), vehicle register, and a minimal admin verification queue. Approving a driver grants
the `DRIVER` role and marks the linked vehicle `APPROVED`. Review outcomes go out by email.

Approved open decisions consumed: OD-003, OD-009, OD-022, OD-024 (product-owner go-ahead
2026-10-02: recommended options treated as approved).

## Explicitly not in this phase

| Item | Why |
| --- | --- |
| Full admin platform (users, trips, settings, flags) | Phase 9; this phase ships the verification/vehicle queue only |
| In-app notification inbox / preferences | Phase 7; review emails use `EmailSender` now |
| Licence-expiry reminder email | Date is collected; `verification.licence_expiry_notice_days = 30` is configured; the cron waits for Phase 7 so a notice is sent once, not every night |
| Attaching a vehicle to a published trip | Phase 4 (`FR-DRV-06` is enforced when trips land) |
| Plate shown to accepted passengers | No trips yet; visibility rule BR-VEH-02 is recorded and the plate is omitted from public profiles |
| Antivirus scan of uploads | `SCAN_UNAVAILABLE`; magic-byte + image re-encode + PDF script reject (Pillow; python-magic skipped on Windows) |
| Users re-downloading their own documents | Forbidden by design (reduces exposure) |

## Quality gate

Recorded in `docs/project-status.md` §Phase 3 gate. Automated checks: ruff, mypy, import-linter,
pytest (files/verification/vehicles/authz), Alembic `0003`, OpenAPI export, `pnpm typecheck` /
lint / Vitest. Playwright Phase 3 journeys (identity submit → admin approve; vehicle + driver
grant) are deferred to the combined product-owner test pass.

## How to try it locally

1. Infrastructure: `pnpm infra:up` (Postgres, Redis, MinIO, Mailpit).
2. API: `cd apps/api && python -m uv run alembic upgrade head && python -m uv run uvicorn app.main:create_app --factory --reload --port 8000`
3. Web: `pnpm dev` → http://localhost:3000/ar
4. Sign in. Account → **الهوية / Identity**: upload national ID front + back + selfie, submit.
5. Mailpit (http://localhost:8025) receives the review email after an admin decides.
6. Grant `ADMIN` with the SQL runbook (`INSERT INTO user_roles … 'ADMIN'`), then open
   `/admin/verifications`. Approve identity, then the driver application.
7. Account → **السواقة / Drive**: add a vehicle (registration front + back), upload the licence,
   apply. After admin approval the account holds `DRIVER`.
