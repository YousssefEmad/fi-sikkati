"""Ratings, reports and blocks (api.md §4.10)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.authz.dependencies import require_permission
from app.core.authz.permissions import Permission
from app.core.authz.principal import Principal
from app.core.config import Settings, get_settings
from app.core.pagination import decode_cursor, encode_cursor
from app.modules.safety.dependencies import SafetyServiceDep
from app.modules.safety.schemas import (
    BlockCreate,
    BlockListResponse,
    BlockResponse,
    RatingCreate,
    RatingResponse,
    RatingSummaryResponse,
    ReportCreate,
    ReportListResponse,
    ReportResponse,
)
from app.modules.safety.service import RatingView, ReportView

ratings_router = APIRouter(tags=["safety"])
reports_router = APIRouter(prefix="/reports", tags=["safety"])
me_reports_router = APIRouter(prefix="/me/reports", tags=["safety"])
me_blocks_router = APIRouter(prefix="/me/blocks", tags=["safety"])


def _rating(view: RatingView) -> RatingResponse:
    return RatingResponse(
        id=view.id,
        trip_id=view.trip_id,
        rater_id=view.rater_id,
        ratee_id=view.ratee_id,
        overall=view.overall,
        punctuality=view.punctuality,
        communication=view.communication,
        experience=view.experience,
        comment=view.comment,
        created_at=view.created_at,
    )


def _report(view: ReportView) -> ReportResponse:
    return ReportResponse(
        id=view.id,
        reporter_id=view.reporter_id,
        target_type=view.target_type,
        target_id=view.target_id,
        reason=view.reason,
        description=view.description,
        status=view.status,
        created_at=view.created_at,
        resolved_at=view.resolved_at,
    )


@ratings_router.post(
    "/trips/{trip_id}/ratings",
    response_model=RatingResponse,
    operation_id="ratings_create",
    summary="Rate a person you shared a completed trip with",
)
async def create_rating(
    trip_id: UUID,
    payload: RatingCreate,
    service: SafetyServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.RATINGS_CREATE))],
) -> RatingResponse:
    view = await service.rate(
        rater_id=principal.user_id,
        trip_id=trip_id,
        ratee_id=payload.ratee_id,
        overall=payload.overall,
        punctuality=payload.punctuality,
        communication=payload.communication,
        experience=payload.experience,
        comment=payload.comment,
    )
    return _rating(view)


@ratings_router.get(
    "/users/{user_id}/ratings/summary",
    response_model=RatingSummaryResponse,
    operation_id="ratings_summary",
    summary="Public rating summary (hidden until the minimum count)",
)
async def rating_summary(
    user_id: UUID,
    service: SafetyServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.RATINGS_READ))],
) -> RatingSummaryResponse:
    del principal
    view = await service.summary(user_id)
    return RatingSummaryResponse(
        user_id=view.user_id, count=view.count, average=view.average, visible=view.visible
    )


@reports_router.post(
    "",
    response_model=ReportResponse,
    operation_id="reports_create",
    summary="File a report",
)
async def create_report(
    payload: ReportCreate,
    service: SafetyServiceDep,
    settings: Annotated[Settings, Depends(get_settings)],
    principal: Annotated[Principal, Depends(require_permission(Permission.REPORTS_CREATE))],
) -> ReportResponse:
    view = await service.report(
        reporter_id=principal.user_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
        description=payload.description,
        hash_secret=settings.auth_hash_secret.get_secret_value(),
    )
    return _report(view)


@me_reports_router.get(
    "",
    response_model=ReportListResponse,
    operation_id="reports_list_mine",
    summary="The signed-in user's reports",
)
async def list_my_reports(
    service: SafetyServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.REPORTS_READ_OWN))],
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ReportListResponse:
    rows = await service.list_mine(principal.user_id, before=decode_cursor(cursor), limit=limit + 1)
    page = rows[:limit]
    next_cursor = None
    if len(rows) > limit and page:
        next_cursor = encode_cursor(page[-1].created_at, page[-1].id)
    return ReportListResponse(items=[_report(row) for row in page], next_cursor=next_cursor)


@me_blocks_router.get(
    "",
    response_model=BlockListResponse,
    operation_id="blocks_list",
    summary="People the signed-in user has blocked",
)
async def list_blocks(
    service: SafetyServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.BLOCKS_MANAGE))],
) -> BlockListResponse:
    rows = await service.list_blocks(principal.user_id)
    return BlockListResponse(
        items=[
            BlockResponse(
                user_id=row.user_id, display_name=row.display_name, created_at=row.created_at
            )
            for row in rows
        ]
    )


@me_blocks_router.post(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="blocks_create",
    summary="Block a user",
)
async def create_block(
    payload: BlockCreate,
    service: SafetyServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.BLOCKS_MANAGE))],
) -> None:
    await service.block(principal.user_id, payload.user_id)


@me_blocks_router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="blocks_delete",
    summary="Unblock a user",
)
async def delete_block(
    user_id: UUID,
    service: SafetyServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.BLOCKS_MANAGE))],
) -> None:
    await service.unblock(principal.user_id, user_id)
