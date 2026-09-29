"""The error contract from api.md §3 / ADR-0010."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.core.config import Settings
from app.core.errors import PROBLEM_CONTENT_TYPE, ConflictError, FieldError
from app.main import create_app


class _Payload(BaseModel):
    seats: int


@pytest.fixture
async def error_client(settings: Settings) -> AsyncIterator[AsyncClient]:
    """App with extra routes that trigger each error path."""
    application: FastAPI = create_app(settings)

    @application.post("/_test/validate")
    async def _validate(payload: _Payload) -> dict[str, int]:
        return {"seats": payload.seats}

    @application.get("/_test/conflict")
    async def _conflict() -> None:
        raise ConflictError(
            "Only 1 seat is available.",
            code="SEAT_UNAVAILABLE",
            title="Not enough seats",
            errors=[FieldError(field="seatsRequested", code="MAX_EXCEEDED", message="max 1")],
        )

    @application.get("/_test/crash")
    async def _crash() -> None:
        msg = "database password is hunter2"
        raise RuntimeError(msg)

    async with LifespanManager(application):
        application.state.health_checks = {}
        transport = ASGITransport(app=application, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as http:
            yield http


async def test_unknown_route_is_problem_json(error_client: AsyncClient) -> None:
    response = await error_client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM_CONTENT_TYPE)
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert body["status"] == 404
    assert body["requestId"] == response.headers["X-Request-Id"]


async def test_validation_error_lists_fields(error_client: AsyncClient) -> None:
    response = await error_client.post("/_test/validate", json={"seats": "many"})
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["errors"][0]["field"] == "seats"
    assert body["errors"][0]["code"]


async def test_app_error_carries_custom_code_and_field_errors(error_client: AsyncClient) -> None:
    response = await error_client.get("/_test/conflict")
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "SEAT_UNAVAILABLE"
    assert body["title"] == "Not enough seats"
    assert body["type"].endswith("/errors/seat-unavailable")
    assert body["errors"] == [
        {"field": "seatsRequested", "code": "MAX_EXCEEDED", "message": "max 1"}
    ]


async def test_unexpected_exception_never_leaks_details(error_client: AsyncClient) -> None:
    response = await error_client.get("/_test/crash")
    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "INTERNAL_ERROR"
    assert "hunter2" not in response.text
    assert "RuntimeError" not in response.text
    assert body["requestId"]
