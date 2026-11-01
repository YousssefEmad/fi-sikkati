"""``/me/verification`` and ``/admin/verifications`` (api.md §4.3, §4.11)."""

from __future__ import annotations

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.core.authz.dependencies import require_permission
from app.core.authz.permissions import Permission
from app.core.authz.principal import Principal
from app.modules.files.dependencies import FileServiceDep
from app.modules.files.schemas import SignedUrlResponse
from app.modules.verification.dependencies import VerificationServiceDep, request_id_of
from app.modules.verification.models import IdentityDocumentType
from app.modules.verification.schemas import (
    AdminDriverQueueItem,
    AdminDriverQueueResponse,
    AdminIdentityQueueItem,
    AdminIdentityQueueResponse,
    DriverStatusResponse,
    DriverSubmitRequest,
    IdentityDocumentResponse,
    LicenceUploadResponse,
    ReviewRejectRequest,
    VehicleRegistrationRequest,
    VerificationStatusResponse,
)
from app.modules.verification.service import (
    DriverStatusView,
    IdentityDocumentView,
    VerificationStatusView,
)

me_router = APIRouter(prefix="/me/verification", tags=["verification"])
admin_router = APIRouter(
    prefix="/admin/verifications",
    tags=["admin"],
)


def _document(view: IdentityDocumentView) -> IdentityDocumentResponse:
    return IdentityDocumentResponse(
        id=view.id,
        document_type=view.document_type,
        file_id=view.file_id,
        original_name=view.original_name,
        mime_type=view.mime_type,
        byte_size=view.byte_size,
        status=view.status,
        uploaded_at=view.uploaded_at,
    )


def _driver(view: DriverStatusView) -> DriverStatusResponse:
    return DriverStatusResponse(
        status=view.status,
        licence_expires_on=view.licence_expires_on,
        licence_file_id=view.licence_file_id,
        licence_original_name=view.licence_original_name,
        vehicle_id=view.vehicle_id,
        rejection_reason=view.rejection_reason,
        submitted_at=view.submitted_at,
    )


def _status(view: VerificationStatusView) -> VerificationStatusResponse:
    return VerificationStatusResponse(
        identity_status=view.identity_status,
        identity_documents=[_document(item) for item in view.identity_documents],
        identity_rejection_reason=view.identity_rejection_reason,
        review_sla_hours=view.review_sla_hours,
        driver=_driver(view.driver),
    )


@me_router.get(
    "",
    response_model=VerificationStatusResponse,
    operation_id="verification_get_me",
    summary="Read identity and driver verification status",
)
async def get_my_verification(
    service: VerificationServiceDep,
    _identity: Annotated[
        Principal, Depends(require_permission(Permission.VERIFICATION_IDENTITY_READ))
    ],
    principal: Annotated[
        Principal, Depends(require_permission(Permission.VERIFICATION_DRIVER_READ))
    ],
) -> VerificationStatusResponse:
    return _status(await service.get_status(principal.user_id))


@me_router.post(
    "/identity/documents",
    response_model=VerificationStatusResponse,
    operation_id="verification_upload_identity_document",
    summary="Upload one identity document",
)
async def upload_identity_document(
    request: Request,
    service: VerificationServiceDep,
    principal: Annotated[
        Principal, Depends(require_permission(Permission.VERIFICATION_IDENTITY_SUBMIT))
    ],
    document_type: Annotated[IdentityDocumentType, Form(alias="documentType")],
    file: Annotated[UploadFile, File()],
) -> VerificationStatusResponse:
    data = await file.read()
    return _status(
        await service.upload_identity_document(
            principal.user_id,
            document_type=document_type,
            data=data,
            filename=file.filename,
            request_id=request_id_of(request),
        )
    )


@me_router.post(
    "/identity/submit",
    response_model=VerificationStatusResponse,
    operation_id="verification_submit_identity",
    summary="Submit identity documents for review",
)
async def submit_identity(
    request: Request,
    service: VerificationServiceDep,
    principal: Annotated[
        Principal, Depends(require_permission(Permission.VERIFICATION_IDENTITY_SUBMIT))
    ],
) -> VerificationStatusResponse:
    return _status(
        await service.submit_identity(principal.user_id, request_id=request_id_of(request))
    )


@me_router.post(
    "/driver/documents",
    response_model=LicenceUploadResponse,
    operation_id="verification_upload_licence",
    summary="Upload the driving licence for a driver application",
)
async def upload_licence(
    request: Request,
    service: VerificationServiceDep,
    principal: Annotated[
        Principal, Depends(require_permission(Permission.VERIFICATION_DRIVER_SUBMIT))
    ],
    file: Annotated[UploadFile, File()],
) -> LicenceUploadResponse:
    stored = await service.upload_licence(
        principal.user_id,
        data=await file.read(),
        filename=file.filename,
        request_id=request_id_of(request),
    )
    return LicenceUploadResponse(
        file_id=stored.id,
        original_name=stored.original_name,
        mime_type=stored.mime_type,
        byte_size=stored.byte_size,
    )


@me_router.post(
    "/driver/submit",
    response_model=VerificationStatusResponse,
    operation_id="verification_submit_driver",
    summary="Submit a driver application",
)
async def submit_driver(
    request: Request,
    payload: DriverSubmitRequest,
    service: VerificationServiceDep,
    principal: Annotated[
        Principal, Depends(require_permission(Permission.VERIFICATION_DRIVER_SUBMIT))
    ],
) -> VerificationStatusResponse:
    return _status(
        await service.submit_driver(
            principal.user_id,
            vehicle_id=payload.vehicle_id,
            licence_expires_on=payload.licence_expires_on,
            licence_file_id=payload.licence_file_id,
            request_id=request_id_of(request),
        )
    )


def _pages(total: int, page_size: int) -> int:
    return max(1, math.ceil(total / page_size)) if total else 0


@admin_router.get(
    "/identity",
    response_model=AdminIdentityQueueResponse,
    operation_id="admin_list_identity_verifications",
    summary="Identity verification queue",
    openapi_extra={"x-internal": True},
)
async def admin_list_identity(
    service: VerificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VERIFICATION_REVIEW))],
    page: int = 1,
    page_size: int = 20,
) -> AdminIdentityQueueResponse:
    del principal
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    items, total = await service.list_pending_identity(page=page, page_size=page_size)
    return AdminIdentityQueueResponse(
        items=[
            AdminIdentityQueueItem(
                user_id=item.user_id,
                display_name=item.display_name,
                email=item.email,
                submitted_at=item.submitted_at,
                document_count=item.document_count,
            )
            for item in items
        ],
        page=page,
        page_size=page_size,
        total_count=total,
        total_pages=_pages(total, page_size),
    )


@admin_router.get(
    "/identity/{user_id}",
    response_model=VerificationStatusResponse,
    operation_id="admin_get_identity_verification",
    summary="Identity verification detail",
    openapi_extra={"x-internal": True},
)
async def admin_get_identity(
    user_id: UUID,
    service: VerificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VERIFICATION_REVIEW))],
) -> VerificationStatusResponse:
    del principal
    return _status(await service.get_status(user_id))


@admin_router.post(
    "/identity/{user_id}/approve",
    response_model=VerificationStatusResponse,
    operation_id="admin_approve_identity",
    summary="Approve identity verification",
    openapi_extra={"x-internal": True},
)
async def admin_approve_identity(
    user_id: UUID,
    request: Request,
    service: VerificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VERIFICATION_REVIEW))],
) -> VerificationStatusResponse:
    return _status(
        await service.approve_identity(
            user_id, reviewer_id=principal.user_id, request_id=request_id_of(request)
        )
    )


@admin_router.post(
    "/identity/{user_id}/reject",
    response_model=VerificationStatusResponse,
    operation_id="admin_reject_identity",
    summary="Reject identity verification",
    openapi_extra={"x-internal": True},
)
async def admin_reject_identity(
    user_id: UUID,
    payload: ReviewRejectRequest,
    request: Request,
    service: VerificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VERIFICATION_REVIEW))],
) -> VerificationStatusResponse:
    return _status(
        await service.reject_identity(
            user_id,
            reviewer_id=principal.user_id,
            reason=payload.reason,
            request_id=request_id_of(request),
        )
    )


@admin_router.get(
    "/driver",
    response_model=AdminDriverQueueResponse,
    operation_id="admin_list_driver_verifications",
    summary="Driver verification queue",
    openapi_extra={"x-internal": True},
)
async def admin_list_driver(
    service: VerificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VERIFICATION_REVIEW))],
    page: int = 1,
    page_size: int = 20,
) -> AdminDriverQueueResponse:
    del principal
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    items, total = await service.list_pending_drivers(page=page, page_size=page_size)
    return AdminDriverQueueResponse(
        items=[
            AdminDriverQueueItem(
                user_id=item.user_id,
                verification_id=item.verification_id,
                display_name=item.display_name,
                email=item.email,
                submitted_at=item.submitted_at,
                vehicle_id=item.vehicle_id,
                licence_expires_on=item.licence_expires_on,
            )
            for item in items
        ],
        page=page,
        page_size=page_size,
        total_count=total,
        total_pages=_pages(total, page_size),
    )


@admin_router.get(
    "/driver/{user_id}",
    response_model=VerificationStatusResponse,
    operation_id="admin_get_driver_verification",
    summary="Driver verification detail",
    openapi_extra={"x-internal": True},
)
async def admin_get_driver(
    user_id: UUID,
    service: VerificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VERIFICATION_REVIEW))],
) -> VerificationStatusResponse:
    del principal
    return _status(await service.get_status(user_id))


@admin_router.post(
    "/driver/{user_id}/approve",
    response_model=VerificationStatusResponse,
    operation_id="admin_approve_driver",
    summary="Approve a driver application and grant DRIVER",
    openapi_extra={"x-internal": True},
)
async def admin_approve_driver(
    user_id: UUID,
    request: Request,
    service: VerificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VERIFICATION_REVIEW))],
) -> VerificationStatusResponse:
    return _status(
        await service.approve_driver(
            user_id, reviewer_id=principal.user_id, request_id=request_id_of(request)
        )
    )


@admin_router.post(
    "/driver/{user_id}/registration",
    response_model=VerificationStatusResponse,
    operation_id="admin_approve_vehicle_registration",
    summary="Approve a saved vehicle, identity if it is waiting, and grant DRIVER",
    openapi_extra={"x-internal": True},
)
async def admin_approve_vehicle_registration(
    user_id: UUID,
    payload: VehicleRegistrationRequest,
    request: Request,
    service: VerificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VERIFICATION_REVIEW))],
) -> VerificationStatusResponse:
    return _status(
        await service.approve_vehicle_registration(
            user_id,
            payload.vehicle_id,
            reviewer_id=principal.user_id,
            request_id=request_id_of(request),
        )
    )


@admin_router.post(
    "/driver/{user_id}/reject",
    response_model=VerificationStatusResponse,
    operation_id="admin_reject_driver",
    summary="Reject a driver application",
    openapi_extra={"x-internal": True},
)
async def admin_reject_driver(
    user_id: UUID,
    payload: ReviewRejectRequest,
    request: Request,
    service: VerificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VERIFICATION_REVIEW))],
) -> VerificationStatusResponse:
    return _status(
        await service.reject_driver(
            user_id,
            reviewer_id=principal.user_id,
            reason=payload.reason,
            request_id=request_id_of(request),
        )
    )


@admin_router.get(
    "/files/{file_id}/download-url",
    response_model=SignedUrlResponse,
    operation_id="admin_document_download_url",
    summary="Issue a short-lived download URL (audited)",
    openapi_extra={"x-internal": True},
)
async def admin_download_url(
    file_id: UUID,
    request: Request,
    files: FileServiceDep,
    principal: Annotated[
        Principal, Depends(require_permission(Permission.VERIFICATION_DOCUMENT_DOWNLOAD))
    ],
) -> SignedUrlResponse:
    signed = await files.issue_download_url(
        file_id, actor_id=principal.user_id, request_id=request_id_of(request)
    )
    return SignedUrlResponse(url=signed.url, expires_in_seconds=signed.expires_in_seconds)
