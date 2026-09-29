# ADR-0009 — OpenAPI-generated TypeScript client as the frontend/backend contract

**Status**: Accepted · **Date**: 2026-09-29

## Context

MEP §85–§86 require documented contracts, prefer generated types, and forbid the frontend
guessing backend behaviour.

## Decision

FastAPI's OpenAPI 3.1 document is exported by `scripts/openapi-export` to
`packages/types/openapi.json` (committed). `openapi-typescript` generates types and
`openapi-fetch` provides a typed client; both live in `packages/types`. CI fails when the
committed schema differs from the running app's schema or when the web app fails to compile
against regenerated types. Zod schemas in the web app cover form UX only and are checked in
tests against the generated types where they overlap.

## Alternatives

- Hand-written TS types: drift. — Full client generators (Orval, openapi-generator): heavier
  output; may adopt if hooks generation proves valuable.
- tRPC/GraphQL: different protocol; REST mandated (MEP §40).

## Consequences

- API changes are visible as diffs in `openapi.json` in the same PR.
- `docs/api-changelog.md` records breaking changes.
