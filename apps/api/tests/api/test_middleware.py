from __future__ import annotations

from httpx import AsyncClient

from app.core.middleware import SECURITY_HEADERS


async def test_response_has_generated_request_id(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    request_id = response.headers["X-Request-Id"]
    assert len(request_id) >= 8


async def test_well_formed_client_request_id_is_echoed(client: AsyncClient) -> None:
    response = await client.get("/health/live", headers={"X-Request-Id": "client-abc-12345"})
    assert response.headers["X-Request-Id"] == "client-abc-12345"


async def test_malformed_client_request_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get("/health/live", headers={"X-Request-Id": "bad id\nwith newline"})
    assert response.headers["X-Request-Id"] != "bad id\nwith newline"
    assert "\n" not in response.headers["X-Request-Id"]


async def test_security_headers_present_on_every_response(client: AsyncClient) -> None:
    response = await client.get("/api/v1/platform/config")
    for name, value in SECURITY_HEADERS.items():
        assert response.headers.get(name) == value, name


async def test_cors_preflight_allows_configured_origin_only(client: AsyncClient) -> None:
    allowed = await client.options(
        "/api/v1/platform/config",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"

    denied = await client.options(
        "/api/v1/platform/config",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in denied.headers
