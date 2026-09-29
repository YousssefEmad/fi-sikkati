# ADR-0003 — Python 3.12 runtime, uv, ruff, mypy strict

**Status**: Accepted · **Date**: 2026-09-29

## Context

The developer machine has Python 3.14.0. Key dependencies (SQLAlchemy 2.x, asyncpg, geoalchemy2,
pydantic, arq, argon2-cffi, python-magic) have their widest verified wheel/compatibility
coverage on 3.12; 3.14 is very new and some compiled dependencies may lag. Production runs in
Docker, so the local interpreter is irrelevant if tooling pins the version.

## Decision

- Target **Python 3.12** for `apps/api` (`requires-python = ">=3.12,<3.13"`), upgraded
  deliberately when dependencies are verified.
- **uv** manages the interpreter (`uv python install 3.12`), the virtualenv and the lockfile
  (`uv.lock` committed). Docker builds use `uv sync --frozen`.
- **ruff** for linting and formatting (replaces flake8/isort/black); **mypy --strict** for
  typing (pydantic and SQLAlchemy plugins); **pytest** with `pytest-asyncio` in auto mode.
- `import-linter` enforces module boundaries (ADR-0001).

## Alternatives

- Poetry/pip-tools: slower, two tools; uv covers both interpreter and dependency management.
- Python 3.14 locally: risk of local-only failures (risk R-12).
- pyright instead of mypy: viable; mypy chosen for plugin maturity with SQLAlchemy 2.x.

## Consequences

- Developers do not need a specific system Python; uv installs 3.12.
- All quality commands are `uv run …`, identical locally and in CI.
