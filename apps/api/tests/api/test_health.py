from __future__ import annotations

from fastapi import FastAPI
from httpx import AsyncClient


async def test_live_returns_ok_without_dependencies(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_reports_each_component(client: AsyncClient, app: FastAPI) -> None:
    async def ok() -> None:
        return None

    app.state.health_checks = {"database": ok, "redis": ok}
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "components": {"database": "ok", "redis": "ok"}}


async def test_ready_returns_503_when_a_dependency_fails(client: AsyncClient, app: FastAPI) -> None:
    async def ok() -> None:
        return None

    async def broken() -> None:
        raise ConnectionError("redis down")

    app.state.health_checks = {"database": ok, "redis": broken}
    response = await client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["components"] == {"database": "ok", "redis": "error"}


async def test_health_endpoints_are_not_in_openapi(client: AsyncClient) -> None:
    response = await client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    document = response.json()
    paths = document["paths"]
    assert "/health/live" not in paths
    assert "/api/v1/platform/config" in paths


async def test_openapi_documents_problem_responses_not_422(client: AsyncClient) -> None:
    document = (await client.get("/api/v1/openapi.json")).json()
    assert "Problem" in document["components"]["schemas"]
    operation = document["paths"]["/api/v1/platform/config"]["get"]
    assert "422" not in operation["responses"]
    assert operation["responses"]["default"]["content"]["application/problem+json"]
