# Runbooks

Operational procedures. Created as the corresponding capability is implemented; each runbook
states preconditions, steps, verification and rollback.

| Runbook | Phase | Status |
| --- | --- | --- |
| [`local-development.md`](local-development.md) — start/stop stack, reset DB, quality gates | 1 | DONE (seeding arrives with Phase 2) |
| [`run-migrations.md`](run-migrations.md) — apply/rollback Alembic revisions | 1 | DONE |
| `bootstrap-admin.md` — create the first admin account | 2 | NOT IMPLEMENTED |
| `rotate-signing-keys.md` — JWT key rotation | 2 | NOT IMPLEMENTED |
| `document-purge.md` — retention job, manual purge | 3 | NOT IMPLEMENTED |
| `rebuffer-route-corridors.md` — after changing matching thresholds | 5 | NOT IMPLEMENTED |
| `incident-realtime.md` — WebSocket/Redis pub-sub degradation | 7 | NOT IMPLEMENTED |
| `moderation-playbook.md` — handling reports and suspensions | 8 | NOT IMPLEMENTED |
| `restore-database.md` — PITR restore and verification | 12 | NOT IMPLEMENTED |
| `release-and-rollback.md` — deploy, smoke, rollback | 12 | NOT IMPLEMENTED |
| `production-checklist.md` — go-live checklist (MEP §100) | 12 | NOT IMPLEMENTED |
