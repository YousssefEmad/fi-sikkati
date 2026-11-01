"""``/me/vehicles`` and ``/admin/vehicles`` (api.md §4.4, §4.11)."""

from __future__ import annotations

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.core.authz.dependencies import require_permission
from app.core.authz.permissions import Permission
from app.core.authz.principal import Principal
from app.core.request_id import get_request_id
from app.modules.vehicles.dependencies import VehicleServiceDep
from app.modules.vehicles.models import VehicleDocumentType
from app.modules.vehicles.schemas import (
    AdminVehicleListResponse,
    ReviewRejectRequest,
    VehicleCreateRequest,
    VehicleDocumentResponse,
    VehicleListResponse,
    VehicleResponse,
    VehicleUpdateRequest,
)
from app.modules.vehicles.service import VehicleDocumentView, VehicleView

me_router = APIRouter(prefix="/me/vehicles", tags=["vehicles"])
admin_router = APIRouter(prefix="/admin/vehicles", tags=["admin"])


def _document(view: VehicleDocumentView) -> VehicleDocumentResponse:
    return VehicleDocumentResponse(
        id=view.id,
        document_type=view.document_type,
        file_id=view.file_id,
        original_name=view.original_name,
        mime_type=view.mime_type,
        byte_size=view.byte_size,
        status=view.status,
        uploaded_at=view.uploaded_at,
    )


def _vehicle(view: VehicleView) -> VehicleResponse:
    return VehicleResponse(
        id=view.id,
        owner_user_id=view.owner_user_id,
        make=view.make,
        model=view.model,
        year=view.year,
        color=view.color,
        vehicle_type=view.vehicle_type,
        seat_capacity=view.seat_capacity,
        plate_number=view.plate_number,
        status=view.status,
        verification_status=view.verification_status,
        documents=[_document(item) for item in view.documents],
    )


@me_router.get(
    "",
    response_model=VehicleListResponse,
    operation_id="vehicles_list_mine",
    summary="List the signed-in user's vehicles",
)
async def list_mine(
    service: VehicleServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VEHICLES_READ))],
) -> VehicleListResponse:
    return VehicleListResponse(
        items=[_vehicle(item) for item in await service.list_mine(principal.user_id)]
    )


@me_router.post(
    "",
    response_model=VehicleResponse,
    operation_id="vehicles_create",
    summary="Register a vehicle",
)
async def create_vehicle(
    payload: VehicleCreateRequest,
    service: VehicleServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VEHICLES_CREATE))],
) -> VehicleResponse:
    return _vehicle(
        await service.create(
            principal.user_id,
            make=payload.make,
            model=payload.model,
            year=payload.year,
            color=payload.color,
            vehicle_type=payload.vehicle_type,
            seat_capacity=payload.seat_capacity,
            plate_number=payload.plate_number,
        )
    )


@me_router.get(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    operation_id="vehicles_get_mine",
    summary="Read one of the signed-in user's vehicles",
)
async def get_mine(
    vehicle_id: UUID,
    service: VehicleServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VEHICLES_READ))],
) -> VehicleResponse:
    return _vehicle(await service.get_mine(principal.user_id, vehicle_id))


@me_router.patch(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    operation_id="vehicles_update_mine",
    summary="Update a vehicle that is not yet approved",
)
async def update_mine(
    vehicle_id: UUID,
    payload: VehicleUpdateRequest,
    service: VehicleServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VEHICLES_UPDATE))],
) -> VehicleResponse:
    return _vehicle(
        await service.update(
            principal.user_id,
            vehicle_id,
            make=payload.make,
            model=payload.model,
            year=payload.year,
            color=payload.color,
            vehicle_type=payload.vehicle_type,
            seat_capacity=payload.seat_capacity,
            plate_number=payload.plate_number,
        )
    )


@me_router.post(
    "/{vehicle_id}/deactivate",
    response_model=VehicleResponse,
    operation_id="vehicles_deactivate_mine",
    summary="Deactivate a vehicle",
)
async def deactivate_mine(
    vehicle_id: UUID,
    service: VehicleServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VEHICLES_UPDATE))],
) -> VehicleResponse:
    return _vehicle(await service.deactivate(principal.user_id, vehicle_id))


@me_router.post(
    "/{vehicle_id}/documents",
    response_model=VehicleResponse,
    operation_id="vehicles_upload_document",
    summary="Upload a vehicle document",
)
async def upload_document(
    vehicle_id: UUID,
    request: Request,
    service: VehicleServiceDep,
    principal: Annotated[
        Principal, Depends(require_permission(Permission.VEHICLES_DOCUMENT_UPLOAD))
    ],
    document_type: Annotated[VehicleDocumentType, Form(alias="documentType")],
    file: Annotated[UploadFile, File()],
) -> VehicleResponse:
    return _vehicle(
        await service.upload_document(
            principal.user_id,
            vehicle_id,
            document_type=document_type,
            data=await file.read(),
            filename=file.filename,
            request_id=get_request_id(request),
        )
    )


@admin_router.get(
    "",
    response_model=AdminVehicleListResponse,
    operation_id="admin_list_vehicles",
    summary="Pending vehicle review queue",
    openapi_extra={"x-internal": True},
)
async def admin_list_vehicles(
    service: VehicleServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VEHICLES_REVIEW))],
    page: int = 1,
    page_size: int = 20,
) -> AdminVehicleListResponse:
    del principal
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    items, total = await service.list_pending(page=page, page_size=page_size)
    return AdminVehicleListResponse(
        items=[_vehicle(item) for item in items],
        page=page,
        page_size=page_size,
        total_count=total,
        total_pages=max(1, math.ceil(total / page_size)) if total else 0,
    )


@admin_router.get(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    operation_id="admin_get_vehicle",
    summary="Vehicle detail for review",
    openapi_extra={"x-internal": True},
)
async def admin_get_vehicle(
    vehicle_id: UUID,
    service: VehicleServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VEHICLES_REVIEW))],
) -> VehicleResponse:
    del principal
    return _vehicle(await service.get(vehicle_id))


@admin_router.post(
    "/{vehicle_id}/approve",
    response_model=VehicleResponse,
    operation_id="admin_approve_vehicle",
    summary="Approve a vehicle",
    openapi_extra={"x-internal": True},
)
async def admin_approve_vehicle(
    vehicle_id: UUID,
    service: VehicleServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VEHICLES_REVIEW))],
) -> VehicleResponse:
    return _vehicle(
        await service.apply_review(
            vehicle_id, approved=True, reviewer_id=principal.user_id, reason=None
        )
    )


@admin_router.post(
    "/{vehicle_id}/reject",
    response_model=VehicleResponse,
    operation_id="admin_reject_vehicle",
    summary="Reject a vehicle",
    openapi_extra={"x-internal": True},
)
async def admin_reject_vehicle(
    vehicle_id: UUID,
    payload: ReviewRejectRequest,
    service: VehicleServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VEHICLES_REVIEW))],
) -> VehicleResponse:
    return _vehicle(
        await service.apply_review(
            vehicle_id, approved=False, reviewer_id=principal.user_id, reason=payload.reason
        )
    )


@admin_router.post(
    "/{vehicle_id}/deactivate",
    response_model=VehicleResponse,
    operation_id="admin_deactivate_vehicle",
    summary="Deactivate a vehicle",
    openapi_extra={"x-internal": True},
)
async def admin_deactivate_vehicle(
    vehicle_id: UUID,
    service: VehicleServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.VEHICLES_UPDATE))],
) -> VehicleResponse:
    del principal
    return _vehicle(await service.admin_deactivate(vehicle_id))
