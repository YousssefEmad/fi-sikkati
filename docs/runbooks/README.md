# Runbooks

Operational procedures. Created as the corresponding capability is implemented; each runbook
states preconditions, steps, verification and rollback.

| Runbook | Phase | Status |
| --- | --- | --- |
| [`local-development.md`](local-development.md) — start/stop stack, reset DB, quality gates | 1 | DONE |
| [`run-migrations.md`](run-migrations.md) — apply/rollback Alembic revisions | 1 | DONE |
| [`bootstrap-admin.md`](bootstrap-admin.md) — grant `ADMIN` on an existing account | 2 | DONE |
| [`rotate-signing-keys.md`](rotate-signing-keys.md) — JWT key rotation | 2 | DONE |
| `document-purge.md` — retention job, manual purge | 3 | NOT IMPLEMENTED |
| `rebuffer-route-corridors.md` — after changing matching thresholds | 5 | NOT IMPLEMENTED |
| `incident-realtime.md` — WebSocket/Redis pub-sub degradation | 7 | NOT IMPLEMENTED |
| `moderation-playbook.md` — handling reports and suspensions | 8 | NOT IMPLEMENTED |
| `restore-database.md` — PITR restore and verification | 12 | NOT IMPLEMENTED |
| `release-and-rollback.md` — deploy, smoke, rollback | 12 | NOT IMPLEMENTED |
| `production-checklist.md` — go-live checklist (MEP §100) | 12 | NOT IMPLEMENTED |
