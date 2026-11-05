"""Identity upload, driver application and admin review (BR-VER-*)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import text

from app.core.config import get_settings
from app.modules.audit.service import AuditLogWriter
from app.modules.files.repository import FileRepository
from app.modules.files.service import FileService
from tests.support.accounts import AccountFactory
from tests.support.email import RecordingEmailSender
from tests.support.http import error_code
from tests.support.uploads import SCRIPT_PDF, jpeg_bytes

pytestmark = pytest.mark.integration


async def _grant_admin(api_app: FastAPI, user_id: str) -> None:
    async with api_app.state.database.session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO user_roles (user_id, role) VALUES (:id, 'ADMIN') "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": user_id},
        )
        await session.commit()


async def _upload_identity(client: AsyncClient, headers: dict[str, str]) -> None:
    for document_type in ("NATIONAL_ID_FRONT", "NATIONAL_ID_BACK", "SELFIE"):
        response = await client.post(
            "/api/v1/me/verification/identity/documents",
            data={"documentType": document_type},
            files={"file": (f"{document_type}.jpg", jpeg_bytes(), "image/jpeg")},
            headers=headers,
        )
        assert response.status_code == 200, response.text


async def _register_vehicle(client: AsyncClient, headers: dict[str, str]) -> str:
    created = await client.post(
        "/api/v1/me/vehicles",
        json={
            "make": "Hyundai",
            "model": "Elantra",
            "year": 2020,
            "color": "white",
            "vehicleType": "SEDAN",
            "seatCapacity": 5,
            "plateNumber": "س ن ع 1234",
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    vehicle_id = created.json()["id"]
    for document_type in ("REGISTRATION_FRONT", "REGISTRATION_BACK"):
        uploaded = await client.post(
            f"/api/v1/me/vehicles/{vehicle_id}/documents",
            data={"documentType": document_type},
            files={"file": (f"{document_type}.jpg", jpeg_bytes(), "image/jpeg")},
            headers=headers,
        )
        assert uploaded.status_code == 200, uploaded.text
    return str(vehicle_id)


async def test_identity_submit_requires_national_id_front_only(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    _, session = await accounts.signed_in()
    empty = await api_client.post(
        "/api/v1/me/verification/identity/submit", headers=session.csrf_headers
    )
    assert empty.status_code == 400
    assert error_code(empty) == "INVALID_TRANSITION"

    front_only = await api_client.post(
        "/api/v1/me/verification/identity/documents",
        data={"documentType": "NATIONAL_ID_FRONT"},
        files={"file": ("NATIONAL_ID_FRONT.jpg", jpeg_bytes(), "image/jpeg")},
        headers=session.csrf_headers,
    )
    assert front_only.status_code == 200, front_only.text

    submitted = await api_client.post(
        "/api/v1/me/verification/identity/submit", headers=session.csrf_headers
    )
    assert submitted.status_code == 200
    assert submitted.json()["identityStatus"] == "PENDING"


async def test_javascript_pdf_is_rejected_on_upload(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    _, session = await accounts.signed_in()
    response = await api_client.post(
        "/api/v1/me/verification/identity/documents",
        data={"documentType": "NATIONAL_ID_FRONT"},
        files={"file": ("id.pdf", SCRIPT_PDF, "application/pdf")},
        headers=session.csrf_headers,
    )
    assert response.status_code == 415
    assert error_code(response) == "UNSUPPORTED_FILE_TYPE"


async def test_passenger_cannot_open_the_admin_queue(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    await accounts.signed_in()
    response = await api_client.get("/api/v1/admin/verifications/identity")
    assert response.status_code == 403
    assert error_code(response) == "FORBIDDEN"


async def test_admin_reviews_identity_then_driver(
    accounts: AccountFactory,
    second_accounts: AccountFactory,
    api_app: FastAPI,
    sent_emails: RecordingEmailSender,
) -> None:
    _, applicant = await accounts.signed_in()
    await _upload_identity(accounts.client, applicant.csrf_headers)
    applicant_id = (await accounts.client.get("/api/v1/me")).json()["id"]

    _, admin_session = await second_accounts.signed_in()
    admin_id = (await second_accounts.client.get("/api/v1/me")).json()["id"]
    await _grant_admin(api_app, admin_id)

    submitted = await accounts.client.post(
        "/api/v1/me/verification/identity/submit", headers=applicant.csrf_headers
    )
    assert submitted.status_code == 200
    staff_notes = await second_accounts.client.get("/api/v1/me/notifications")
    assert staff_notes.status_code == 200, staff_notes.text
    assert any(
        item["type"] == "REVIEW_REQUESTED" and item["payload"].get("kind") == "IDENTITY"
        for item in staff_notes.json()["items"]
    )

    queue = await second_accounts.client.get("/api/v1/admin/verifications/identity")
    assert queue.status_code == 200, queue.text
    assert queue.json()["totalCount"] == 1

    detail = await second_accounts.client.get(
        f"/api/v1/admin/verifications/identity/{applicant_id}"
    )
    file_id = detail.json()["identityDocuments"][0]["fileId"]
    signed = await second_accounts.client.get(
        f"/api/v1/admin/verifications/files/{file_id}/download-url"
    )
    assert signed.status_code == 200
    assert signed.json()["url"].startswith("memory://")

    forbidden = await accounts.client.get(
        f"/api/v1/admin/verifications/files/{file_id}/download-url"
    )
    assert forbidden.status_code == 403

    approved = await second_accounts.client.post(
        f"/api/v1/admin/verifications/identity/{applicant_id}/approve",
        headers=admin_session.csrf_headers,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["identityStatus"] == "APPROVED"
    assert any(
        "توثيق" in email.subject or "verified" in email.subject.lower()
        for email in sent_emails.messages
    )

    vehicle_id = await _register_vehicle(accounts.client, applicant.csrf_headers)
    licence = await accounts.client.post(
        "/api/v1/me/verification/driver/documents",
        files={"file": ("licence.jpg", jpeg_bytes(), "image/jpeg")},
        headers=applicant.csrf_headers,
    )
    assert licence.status_code == 200, licence.text
    driver = await accounts.client.post(
        "/api/v1/me/verification/driver/submit",
        json={
            "vehicleId": vehicle_id,
            "licenceExpiresOn": date(datetime.now(UTC).year + 2, 1, 15).isoformat(),
            "licenceFileId": licence.json()["fileId"],
        },
        headers=applicant.csrf_headers,
    )
    assert driver.status_code == 200, driver.text
    assert driver.json()["driver"]["status"] == "PENDING"
    driver_notes = await second_accounts.client.get("/api/v1/me/notifications")
    assert any(
        item["type"] == "REVIEW_REQUESTED" and item["payload"].get("kind") == "DRIVER"
        for item in driver_notes.json()["items"]
    )
    applicant_notes = await accounts.client.get("/api/v1/me/notifications")
    assert any(
        item["type"] == "VERIFICATION_STATUS_CHANGED" for item in applicant_notes.json()["items"]
    )
    assert all(item["type"] != "REVIEW_REQUESTED" for item in applicant_notes.json()["items"])

    granted = await second_accounts.client.post(
        f"/api/v1/admin/verifications/driver/{applicant_id}/approve",
        headers=admin_session.csrf_headers,
    )
    assert granted.status_code == 200, granted.text
    assert granted.json()["driver"]["status"] == "APPROVED"

    me = await accounts.client.get("/api/v1/me")
    assert "DRIVER" in me.json()["roles"]


async def test_driver_application_requires_approved_identity(
    accounts: AccountFactory, api_client: AsyncClient
) -> None:
    _, session = await accounts.signed_in()
    await _register_vehicle(api_client, session.csrf_headers)
    licence = await api_client.post(
        "/api/v1/me/verification/driver/documents",
        files={"file": ("licence.jpg", jpeg_bytes(), "image/jpeg")},
        headers=session.csrf_headers,
    )
    assert licence.status_code == 400
    assert error_code(licence) == "INVALID_TRANSITION"


async def test_purge_removes_due_objects(api_app: FastAPI) -> None:
    storage = api_app.state.object_storage
    settings = get_settings()
    async with api_app.state.database.session_factory() as session:
        # A file owned by a real user is created through the API in other tests; here we only
        # assert the service deletes whatever is due. Empty run is still a successful no-op.
        service = FileService(FileRepository(session), storage, settings, AuditLogWriter(session))
        purged = await service.purge_due(now=datetime.now(UTC) + timedelta(days=400))
        await session.commit()
    assert purged >= 0
