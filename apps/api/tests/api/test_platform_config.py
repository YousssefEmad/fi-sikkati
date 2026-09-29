from __future__ import annotations

from httpx import AsyncClient


async def test_public_config_is_camel_case_and_non_sensitive(client: AsyncClient) -> None:
    response = await client.get("/api/v1/platform/config")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "environment": "test",
        "apiVersion": "v1",
        "supportedLocales": ["ar", "en"],
        "defaultLocale": "ar",
        "defaultTimezone": "Africa/Cairo",
    }
    # No secrets or connection strings may ever leak through this endpoint.
    assert "postgresql" not in response.text
    assert "redis://" not in response.text
