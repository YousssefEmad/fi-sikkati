# ADR-0006 — UUID v7 primary keys

**Status**: Accepted · **Date**: 2026-09-29

## Context

MEP §42 asks for UUIDs or a documented ID strategy used consistently. Random UUID v4 keys
fragment B-tree indexes and make keyset pagination awkward; sequential integers leak volume and
are enumerable.

## Decision

All primary keys are UUID v7 (time-ordered, RFC 9562) generated **in the application**
(`uuid6`/`uuid_utils` library on Python 3.12; native `uuid.uuid7()` when we move to 3.14), stored
as PostgreSQL `uuid`. Message and notification ids double as cursors.

## Alternatives

- UUID v4: poor index locality. — bigint identity: enumerable, awkward across services.
- ULID: similar benefits, non-native type. — DB-side `uuidv7()` (PostgreSQL 18): would tie us to
  PG 18; may adopt later.

## Consequences

- Cursors are simple `(sort_key, id)` tuples.
- Ids are not secrets; authorization never relies on unguessability.
