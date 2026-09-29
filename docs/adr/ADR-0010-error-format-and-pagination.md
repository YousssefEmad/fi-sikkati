# ADR-0010 — API error format (RFC 9457 Problem Details with `code`) and pagination strategy

**Status**: Accepted · **Date**: 2026-09-29

## Context

MEP §41 requires machine-readable codes, human messages, optional field errors and request ids,
no stack traces; §90 forbids unbounded lists and requires a documented pagination strategy.

## Decision

Errors: `application/problem+json` per RFC 9457 with fields `type, title, status, detail,
code, requestId, errors[]` (`api.md` §3). A single exception handler renders `AppError`
subclasses; unexpected exceptions become `INTERNAL_ERROR` with only `requestId`.

Pagination: **cursor** (opaque base64 of sort key + id) for all user-facing feeds; **page**
based for admin tables that need totals. `pageSize` bounded (50 user, 100 admin). Sorting from
an allow-list.

## Alternatives

- Custom envelope `{ success, data, error }`: non-standard; Problem Details is widely tooled.
- Offset pagination everywhere: unstable under inserts, O(n) skips; unsuitable for chat.

## Consequences

- Frontend maps `code` to translated messages; `detail` is fallback text.
- Cursor implementations share `core/pagination.py`.
