"""Liveness and readiness endpoints (served outside ``/api/v1``).

* ``/health/live`` — the process is up. Never touches dependencies.
* ``/health/ready`` — PostgreSQL and Redis are reachable. Returns 503 with per-component
  status when any dependency fails so orchestrators stop routing traffic.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal

import structlog
from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

log = structlog.get_logger("app.health")

router = APIRouter(prefix="/health", tags=["health"], include_in_schema=False)

ComponentStatus = Literal["ok", "error"]
HealthCheck = Callable[[], Awaitable[None]]

_CHECK_TIMEOUT_SECONDS = 3.0


class LiveResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    status: Literal["ok", "degraded"]
    components: dict[str, ComponentStatus]


async def _run_check(name: str, check: HealthCheck) -> tuple[str, ComponentStatus]:
    try:
        await asyncio.wait_for(check(), timeout=_CHECK_TIMEOUT_SECONDS)
    except Exception as exc:  # any failure means "not ready"
        log.warning("readiness_check_failed", component=name, error=type(exc).__name__)
        return name, "error"
    return name, "ok"


def get_health_checks(request: Request) -> dict[str, HealthCheck]:
    """Readiness checks registered on ``app.state`` at startup; overridable in tests."""
    checks = getattr(request.app.state, "health_checks", None)
    return dict(checks) if isinstance(checks, dict) else {}


@router.get("/live", response_model=LiveResponse)
async def live() -> LiveResponse:
    return LiveResponse()


@router.get("/ready", response_model=ReadyResponse)
async def ready(request: Request, response: Response) -> ReadyResponse:
    checks = get_health_checks(request)
    results = await asyncio.gather(*(_run_check(name, check) for name, check in checks.items()))
    components = dict(results)
    healthy = all(state == "ok" for state in components.values())
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(status="ok" if healthy else "degraded", components=components)
