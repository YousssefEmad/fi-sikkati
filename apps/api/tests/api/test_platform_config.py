from __future__ import annotations

from httpx import AsyncClient


async def test_public_config_is_camel_case_and_non_sensitive(client: AsyncClient) -> None:
    response = await client.get("/api/v1/platform/config")
    assert response.status_code == 200
    body = response.json()
    public_key = body.pop("vapidPublicKey")
    assert public_key is None or (isinstance(public_key, str) and public_key != "")
    assert body == {
        "environment": "test",
        "apiVersion": "v1",
        "supportedLocales": ["ar", "en"],
        "defaultLocale": "ar",
        "defaultTimezone": "Africa/Cairo",
        "passwordMinLength": 10,
        "minimumAgeYears": 18,
        "termsVersion": "2026-10-01",
        "privacyVersion": "2026-10-01",
        "deletionGraceDays": 14,
        "maxDocumentBytes": 10485760,
        "maxVehiclesPerDriver": 3,
        "reviewSlaHours": 48,
        "identityDocumentTypes": ["NATIONAL_ID_FRONT", "NATIONAL_ID_BACK", "SELFIE"],
        "vehicleDocumentTypes": ["REGISTRATION_FRONT", "REGISTRATION_BACK", "VEHICLE_PHOTO"],
        "maxPassengerSeats": 7,
        "suggestedPriceLabel": "suggested_contribution",
        "mapboxPublicToken": None,
        "matchingCorridorWidthMeters": 1000,
        "matchingStopProximityMeters": 500,
        "matchingDefaultTimeWindowMinutes": 60,
    }
    # No secrets or connection strings may ever leak through this endpoint.
    assert "postgresql" not in response.text
    assert "redis://" not in response.text
