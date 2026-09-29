# ADR-0011 — Money as integer minor units

**Status**: Accepted · **Date**: 2026-09-29

## Context

MEP §33 requires integer minor units and forbids floating point in financial calculations; §32
makes pricing configurable; §31 forbids payments until approved.

## Decision

All monetary values are `bigint` minor units (piastres) with an explicit ISO-4217 `currency`
column (`EGP`). Python uses `int`; API uses `{ amountMinor, currency }`; the web formats with
`Intl.NumberFormat`. Percentages are basis points (`int`). Rounding is explicit
(`ROUND_HALF_UP` via `decimal` only at the boundary of computing from distance). A `Money`
value object prevents mixing currencies.

## Alternatives

- `numeric(12,2)`: safe in PostgreSQL but invites floats in application code.
- Float: rejected outright.

## Consequences

- Pricing engine is trivially testable with integers.
- Future payment records reuse the same representation.
