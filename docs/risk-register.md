# Risk Register

Likelihood/Impact: L/M/H. Owner is the engineering role accountable. Reviewed at each phase report.

| ID | Risk | L | I | Mitigation | Trigger / status |
| --- | --- | --- | --- | --- | --- |
| R-01 | Leak of identity documents (public URL, misconfigured bucket, log leakage) | M | H | Private bucket, signed 120 s URLs, audit on view, scrubbed logs, upload re-encoding, CI check that no public ACL is configured, security tests (ADR-0013) | Any document URL without auth in code review |
| R-02 | Seat overbooking under concurrency | M | H | Row lock + CHECK constraint + partial unique index + concurrency test suite gate for Phase 6 | Concurrency tests failing |
| R-03 | Route matching produces false positives (El Obour→6th Oct matched with El Obour→Nasr City) | M | H | Geometry-based corridor + order check, no name matching, deterministic tests with real Cairo geometries, thresholds configurable (OD-006) | User reports of irrelevant results |
| R-04 | Account takeover (weak passwords, token theft) | M | H | Argon2id, refresh rotation with family revocation, rate limits, session management, HttpOnly/Secure cookies | Auth anomalies in audit log |
| R-05 | Privilege escalation to admin | L | H | Code-defined permissions, DB re-check on admin routes, matrix tests, bootstrap-only admin creation | New route without matrix row (CI check) |
| R-06 | Exposure of exact locations/phone numbers | M | H | Server-side blur, party-only exact stops, phone sharing opt-in (OD-011), response models | Privacy complaint |
| R-07 | Business decisions delayed → phases blocked | H | M | Open-decisions list with recommendations delivered early; phases partially implementable up to the boundary | Phase report shows BLOCKED items |
| R-08 | Map provider cost or coverage inadequate in Egypt | M | M | Provider abstraction, Redis caching within provider terms, evaluation spike in Phase 4 | Autocomplete quality feedback |
| R-09 | Arabic/RTL treated as afterthought | M | M | AR is default locale in dev, RTL snapshot tests, logical CSS properties, ICU formatting from Phase 1 | Any hard-coded string in review |
| R-10 | Real-time reliability (dropped WebSocket, missed messages) | M | M | Persist-then-publish, HTTP polling fallback, reconnect with cursor catch-up | Support tickets about missing messages |
| R-11 | Background job library maturity (arq) | M | L | Jobs isolated behind a small interface; idempotent jobs; Celery documented as fallback (ADR-0007) | Unresolved upstream bug |
| R-12 | Python 3.14 locally vs 3.12 target causing inconsistencies | M | L | uv pins Python 3.12; Docker for all test runs; CI on 3.12 | Local-only failures |
| R-13 | Spam / fake trips / harassment | M | M | Rate limits, verification gate for requests (OD-002), reports + moderation, blocks | Report volume |
| R-14 | Data-protection compliance (Egypt PDPL 151/2020) | M | H | Data minimisation, retention (OD-009), deletion policy (OD-020), privacy page, legal review flagged | Legal review outcome |
| R-15 | Scope creep into ride-hailing features | M | M | PRD §1.1 non-goals; every new feature must trace to PRD/OD | Request for "instant ride" features |
| R-16 | Single-region outage / data loss | L | H | Daily base backups + WAL, PITR tested quarterly, restore runbook, image rollback | DR test failure |
| R-17 | Mobile UX poor because desktop-first habits | M | M | Mobile viewport in every E2E scenario, mobile-first components, Lighthouse mobile budget | Lighthouse mobile < 90 |
| R-18 | AI produces incorrect or unsafe suggestions | M | M | Read-only tools, schema validation, trip ids rendered from API not LLM text, rate limits, flag-gated | Incident review |
| R-19 | No external penetration test before launch | M | H | Recommend budget for a third-party test before Phase 12; internal checklist regardless | Budget decision (OD-026 discussion) |
| R-20 | Migration failure in production | L | H | CI up/down/up, expand/contract pattern, migration step separate from deploy, backup before migration | Failed release |
