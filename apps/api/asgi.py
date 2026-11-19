"""Vercel / ASGI entrypoint.

Vercel looks for a module-level ``app`` FastAPI instance. Locally you can still run::

    uvicorn app.main:create_app --factory
"""

from __future__ import annotations

from app.main import create_app

app = create_app()
