# Fi Sikkati API

FastAPI modular monolith. See [`../../docs/architecture.md`](../../docs/architecture.md) §3.

```powershell
uv sync                       # installs Python 3.12 + dependencies into .venv
uv run uvicorn app.main:create_app --factory --reload
uv run pytest                 # unit + API tests (integration tests need DATABASE_URL/REDIS_URL)
uv run ruff check . ; uv run ruff format --check . ; uv run mypy ; uv run lint-imports
uv run alembic upgrade head
```

Configuration is read from environment variables (see `.env.example`). The process refuses to
start with missing or invalid configuration.
