# ADR-0014 — Async SQLAlchemy 2.x with asyncpg and one unit-of-work per request

**Status**: Accepted · **Date**: 2026-09-29

## Context

FastAPI is asyncio-native; WebSockets and provider calls benefit from async I/O. MEP §87
requires explicit transactions for seat reservation, state transitions and multi-table changes.

## Decision

SQLAlchemy 2.x async engine with `asyncpg`; one `AsyncSession` per HTTP request/job provided by
dependency injection, committed by the unit-of-work wrapper on success and rolled back on any
exception. Services own transaction scope; repositories never commit. Row locks use
`with_for_update()`. Post-commit domain events are dispatched by the unit-of-work after
`commit()`. PostGIS through `geoalchemy2`; raw PostGIS SQL allowed in repositories with bound
parameters.

## Alternatives

- Sync SQLAlchemy + threadpool: simpler debugging, but mixing sync DB with async WebSockets and
  providers is clumsy.
- Raw asyncpg without ORM: faster, but loses migrations autogenerate and typed models.

## Consequences

- All DB tests run against real PostgreSQL (async fixtures).
- Care needed with lazy loading in async (use explicit `selectinload`).
