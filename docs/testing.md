# Testing Strategy

Testing is a quality gate, not an afterthought (MEP §56–§57). A phase is not complete until
every layer below that applies to it is green in CI.

## 1. Layers

| Layer | Tooling | Location | Scope |
| --- | --- | --- | --- |
| Backend unit | pytest, pytest-asyncio, hypothesis (selected) | `apps/api/tests/unit` | pure services with fakes: pricing, state machines, ranking comparator, validators, token logic |
| Backend integration (DB) | pytest + real PostgreSQL/PostGIS in Docker (testcontainers or CI service) | `apps/api/tests/integration` | repositories, constraints, migrations, PostGIS queries, seat transaction |
| API tests | httpx `AsyncClient` against the FastAPI app with test DB | `apps/api/tests/api` | request/response contracts, error format, pagination, idempotency |
| Authorization tests | parametrised over `permission-matrix.md` rows | `apps/api/tests/authz` | every protected route × every role → expected status |
| Concurrency tests | pytest with real DB, `asyncio.gather` on N parallel sessions | `apps/api/tests/concurrency` | overbooking, races (§5) |
| Frontend unit/component | Vitest + Testing Library + jsdom | `apps/web/tests` | components, hooks, Zod schemas, formatting (AR/EN), RTL rendering |
| E2E | Playwright (Chromium + Mobile Safari/Chrome viewports) | `tests/e2e` | critical journeys (§3) against the full Compose stack |
| Accessibility | `@axe-core/playwright` in E2E; eslint-plugin-jsx-a11y | E2E + lint | WCAG 2.2 AA smoke on every core screen |
| Security | see `security.md` §12 | `apps/api/tests/security`, CI scanners | uploads, CSRF, IDOR, rate limits, dependency/container scanning |
| Load (Phase 11) | k6 | `tests/load` | search, join-request accept, chat fan-out |
| Contract | OpenAPI diff | CI | committed schema == generated schema; generated client compiles |

## 2. Principles

- Tests run against a **real PostgreSQL + PostGIS** (never SQLite) so constraints, locks and
  geography are tested for real.
- Every test gets an isolated schema/transaction; fixtures via factories (`factory_boy` /
  `polyfactory`), no shared mutable seed.
- Time is injected (`Clock`); tests never `sleep` for business time.
- External providers (maps, email, LLM, storage) have deterministic fakes; one contract test
  per real provider runs only when credentials are present (nightly).
- Test names reference rule ids: `test_br_join_06_accept_is_atomic_under_contention`.
- Coverage is measured and reported; thresholds are gates for the `bookings`, `trips`, `auth`,
  `verification` and `authz` packages (≥ 90 % lines), informative elsewhere. Coverage never
  substitutes for the scenario list below.

## 3. Critical E2E scenarios (MEP §56)

| # | Scenario | Phase |
| --- | --- | --- |
| 1 | Registration (AR + EN) | 2 |
| 2 | Login / logout / session revoke | 2 |
| 3 | Identity verification submit → admin approve → badge visible | 2/3 |
| 4 | Driver creates vehicle + documents → admin approve → DRIVER role | 3 |
| 5 | Driver creates and publishes a trip with route preview | 4 |
| 6 | Passenger searches; incompatible route not returned; compatible returned as EXACT/ON_ROUTE | 5 |
| 7 | Passenger views trip (blurred points before acceptance) | 5 |
| 8 | Passenger requests seats (idempotent on double submit) | 6 |
| 9 | Driver accepts; seats decrease; trip becomes FULL at 0 | 6 |
| 10 | Seat availability updates live in another session | 6/7 |
| 11 | Passenger cancels accepted request; seats released; FULL → PUBLISHED | 6 |
| 12 | Driver cancels trip; requests CANCELLED; notifications; chat read-only | 6/7 |
| 13 | Trip start → complete; requests COMPLETED | 4/6 |
| 14 | Mutual rating; duplicate blocked; rating before completion blocked | 8 |
| 15 | Trip chat: send, receive live, read pointer, system messages | 7 |
| 16 | Notification received in-app + email (fake SMTP) + preference respected | 7 |
| 17 | Admin suspends user; user's trips cancelled; audit entry | 9 |
| 18 | Report message → admin resolves with action; reporter notified | 8/9 |

Each scenario runs on a mobile viewport and a desktop viewport, and in both locales for
scenarios 1, 5, 6 and 8.

## 4. Authorization matrix tests

A single parametrised test module loads a table of `(method, path, role, expected_status)`
derived from `permission-matrix.md` and asserts each row; a check in CI fails if a new route
appears in the OpenAPI document without a matrix entry.

## 5. Concurrency scenarios (MEP §88) — must pass before Phase 6 closes

| Scenario | Expected |
| --- | --- |
| 2 passengers × 1 seat left, accepts issued simultaneously | exactly one `ACCEPTED`, the other `SEAT_UNAVAILABLE`; `available_seats = 0`; trip `FULL` |
| 10 parallel accepts on a 3-seat trip with 10 pending requests | exactly 3 accepted |
| Driver cancels trip while a request is being accepted | request ends `CANCELLED` or accept fails `TRIP_NOT_ACCEPTING`; never `ACCEPTED` on a `CANCELLED` trip |
| Passenger cancels while driver accepts | one of them wins; seat counter consistent with final status |
| Same `Idempotency-Key` sent 5× in parallel | one request row; identical responses |
| Duplicate create without key reuse for same trip | second → `DUPLICATE_REQUEST` |
| Accept called twice | second → `REQUEST_NOT_PENDING` |
| Repeated `clientMessageId` | one message |

These run against real PostgreSQL with multiple connections; assertions also query the DB
directly to confirm invariants (`0 ≤ available_seats ≤ total_seats`, sum of accepted seats ==
`total_seats − available_seats`).

## 6. Security tests

Upload: oversize, wrong extension, MIME mismatch, PDF with JavaScript, filename with `../`,
polyglot image — all rejected with the right codes. IDOR: every `GET /…/{id}` with another
user's id → `404`/`403` per matrix. CSRF: cookie-auth `POST` without token → `403 CSRF_FAILED`.
Auth: expired access token, revoked session, refresh reuse → family revoked. Rate limits:
N+1th request → `429`. Logs: scrubber unit tests with sample payloads.

## 7. Frontend tests

Component tests for every feature's forms (validation messages in AR and EN), empty states,
confirmation dialogs, RTL layout snapshots for key screens, TanStack Query hooks with MSW
(mock service worker) using the **generated** API types so mocks cannot drift. Lighthouse CI on
public pages (performance ≥ 90, accessibility ≥ 95) from Phase 11.

## 8. Quality gates per phase (MEP §57, §94)

```
pnpm -r lint  &&  pnpm -r typecheck  &&  pnpm -r test  &&  pnpm -r build
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
alembic upgrade head && alembic check && alembic downgrade base && alembic upgrade head
pnpm exec playwright test   # E2E against compose stack
import-linter, gitleaks, pip-audit, pnpm audit, trivy
```

CI (`.github/workflows/ci.yml`, Phase 1) runs all of the above on every PR to `develop`/`main`;
a red job blocks merge. The phase completion report lists the CI run that proves the gate.

## 9. Test data

Development seed (`scripts/seed_dev.py`): a few users per role, verified driver with vehicle,
sample trips around El Obour with real route geometry from the fake provider, sample requests
and messages. Seeds are idempotent and refuse to run when `APP_ENV=production` (MEP §84).
Staging uses anonymised synthetic data only.
