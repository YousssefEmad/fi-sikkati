# ADR-0002 — Monorepo layout and JavaScript tooling (pnpm workspaces)

**Status**: Accepted · **Date**: 2026-09-29

## Context

MEP §7 recommends `/apps`, `/packages`, `/docs`, `/infra`, `/scripts`, `/tests`. The web app is
TypeScript; the API is Python, so "shared code" between them is limited to the API contract and
tooling configuration. The developer machine has Node 24.11 and npm 11 but not pnpm.

## Decision

- Layout follows MEP §7 exactly: `apps/web`, `apps/api`, `packages/types` (TypeScript types
  generated from the OpenAPI document plus the thin `openapi-fetch` client built on them),
  `packages/config` (shared ESLint/Prettier/tsconfig), `docs`, `infra`, `scripts`, `tests/e2e`.
  `packages/shared` is created the first time two workspaces need the same runtime code; an
  empty package would be an unnecessary abstraction (MEP §7 "avoid unnecessary abstractions").
- JavaScript package manager: **pnpm** (workspaces, strict node_modules, fast CI), pinned via
  `packageManager` in the root `package.json` and installed with `corepack enable` or
  `npm i -g pnpm` (documented in README). Node version pinned in `.nvmrc`/`engines` to 24 LTS.
- Python packages are not part of the JS workspace; `apps/api` is managed by uv (ADR-0003).
- Root scripts orchestrate both (`pnpm lint`, `pnpm test`, `make`-free; a small `scripts/`
  directory with cross-platform Node/Python scripts because developers use Windows and Linux).

## Alternatives

- npm workspaces: available without install, but slower and less strict; acceptable fallback.
- Turborepo/Nx: added later only if build times justify it.
- Separate repositories: contract drift between web and API; harder phase gating.

## Consequences

- One PR can change API + contract + web atomically.
- Developers install pnpm once; CI uses `pnpm/action-setup`.
- Windows compatibility: scripts avoid bash-only constructs.
