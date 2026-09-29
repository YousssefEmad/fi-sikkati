# ADR-0007 — Background jobs with arq on Redis

**Status**: Accepted · **Date**: 2026-09-29

## Context

MEP §36–§37 name Redis for background jobs; jobs must be retryable, idempotent, observable.
The API is asyncio (ADR-0014) and shares its service layer with jobs.

## Decision

Use **arq** (asyncio-native, Redis-backed) for delayed/queued jobs and cron. Jobs are defined in
each module's `jobs.py`, registered in `app/workers/main.py`, and call the same service functions
as HTTP routes. Every job is idempotent by construction (keyed on entity id + expected state) and
uses `max_tries` with exponential backoff. A thin `JobQueue` protocol wraps arq so it can be
replaced without touching modules. Job outcomes are logged with `request_id` propagated from
the originating request.

## Alternatives

- Celery: mature but sync-first; running async SQLAlchemy inside Celery workers is awkward.
  Documented fallback if arq maturity becomes a problem (risk R-11).
- Dramatiq / taskiq: viable; taskiq is younger, Dramatiq sync-first.
- PostgreSQL-backed queue (procrastinate): transactional enqueue is attractive; rejected for now
  to keep PostgreSQL load for transactional data per MEP §36; revisit if exactly-once enqueue
  becomes a requirement.

## Consequences

- Post-commit event handlers enqueue jobs; a crash between commit and enqueue can drop a job,
  so cron sweepers (expire trips, resend pending notifications) re-derive work from DB state.
- Worker is a separate container from the same image.
