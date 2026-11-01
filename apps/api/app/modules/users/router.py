"""``/me`` and ``/users`` endpoints (api.md §4.2)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz.dependencies import require_permission
from app.core.authz.permissions import Permission
from app.core.authz.ports import SessionRevoker, get_session_revoker
from app.core.authz.principal import Principal
from app.core.cookies import clear_session_cookies
from app.core.database import get_db_session
from app.core.request_id import get_request_id
from app.modules.files.dependencies import FileServiceDep
from app.modules.files.service import FileService
from app.modules.users.dependencies import UserServiceDep
from app.modules.users.schemas import (
    AccountResponse,
    DeleteAccountResponse,
    ProfileUpdateRequest,
    PublicProfileResponse,
)
from app.modules.users.service import AccountView

me_router = APIRouter(prefix="/me", tags=["users"])
users_router = APIRouter(prefix="/users", tags=["users"])

#: Reason recorded on the sessions that account closure revokes (database.md §2.1).
_ACCOUNT_CLOSED = "ACCOUNT_CLOSED"


async def _account_response(view: AccountView, files: FileService) -> AccountResponse:
    photo_url = await files.public_url_for(view.photo_file_id) if view.photo_file_id else None
    return AccountResponse(
        id=view.id,
        email=view.email,
        phone=view.phone,
        status=view.status,
        email_verified=view.email_verified,
        phone_verified=view.phone_verified,
        identity_verification_status=view.identity_verification_status,
        roles=sorted(view.roles),
        locale=view.locale,
        display_name=view.display_name,
        full_name=view.full_name,
        city=view.city,
        bio=view.bio,
        date_of_birth=view.date_of_birth,
        created_at=view.created_at,
        last_login_at=view.last_login_at,
        deletion_requested_at=view.deletion_requested_at,
        photo_url=photo_url,
        share_phone_with_trip_peers=view.share_phone_with_trip_peers,
    )


@me_router.get(
    "",
    response_model=AccountResponse,
    operation_id="users_get_me",
    summary="Read the signed-in account",
)
async def get_me(
    service: UserServiceDep,
    files: FileServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ME_READ))],
) -> AccountResponse:
    return await _account_response(await service.get_account(principal.user_id), files)


@me_router.patch(
    "",
    response_model=AccountResponse,
    operation_id="users_update_me",
    summary="Update the signed-in account's profile",
)
async def update_me(
    payload: ProfileUpdateRequest,
    service: UserServiceDep,
    files: FileServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ME_UPDATE))],
) -> AccountResponse:
    view = await service.update_profile(
        principal.user_id,
        display_name=payload.display_name,
        full_name=payload.full_name,
        city=payload.city,
        bio=payload.bio,
        locale=payload.locale,
        phone_e164=payload.phone,
        share_phone_with_trip_peers=payload.share_phone_with_trip_peers,
    )
    return await _account_response(view, files)


@me_router.post(
    "/photo",
    response_model=AccountResponse,
    operation_id="users_upload_photo",
    summary="Upload a profile photo",
)
async def upload_photo(
    request: Request,
    service: UserServiceDep,
    files: FileServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ME_UPDATE))],
    file: Annotated[UploadFile, File()],
) -> AccountResponse:
    stored = await files.store_public_photo(
        owner_user_id=principal.user_id,
        data=await file.read(),
        filename=file.filename,
        actor_id=principal.user_id,
        request_id=get_request_id(request),
    )
    return await _account_response(await service.set_photo(principal.user_id, stored.id), files)


@me_router.delete(
    "",
    response_model=DeleteAccountResponse,
    operation_id="users_delete_me",
    summary="Close the signed-in account",
    description=(
        "BR-ACC-07: the account is closed immediately, every session is revoked, and the data "
        "is anonymised after the grace period. Signing in before then cancels the deletion."
    ),
)
async def delete_me(
    response: Response,
    service: UserServiceDep,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    revoke_sessions: Annotated[SessionRevoker, Depends(get_session_revoker)],
    principal: Annotated[Principal, Depends(require_permission(Permission.ME_DELETE))],
) -> DeleteAccountResponse:
    anonymised_after = await service.request_deletion(principal.user_id)
    await revoke_sessions(db, principal.user_id, _ACCOUNT_CLOSED)
    clear_session_cookies(response)
    return DeleteAccountResponse(anonymised_after=anonymised_after)


@users_router.get(
    "/{user_id}/public-profile",
    response_model=PublicProfileResponse,
    operation_id="users_get_public_profile",
    status_code=status.HTTP_200_OK,
    summary="Read another user's public profile",
)
async def get_public_profile(
    user_id: UUID,
    service: UserServiceDep,
    files: FileServiceDep,
    principal: Annotated[
        Principal, Depends(require_permission(Permission.USERS_READ_PUBLIC_PROFILE))
    ],
) -> PublicProfileResponse:
    del principal  # authorization only; the profile is the same for every signed-in caller
    view = await service.get_public_profile(user_id)
    photo_url = await files.public_url_for(view.photo_file_id) if view.photo_file_id else None
    return PublicProfileResponse(
        user_id=view.user_id,
        display_name=view.display_name,
        city=view.city,
        is_driver=view.is_driver,
        identity_verified=view.identity_verified,
        member_since=view.member_since,
        photo_url=photo_url,
        cancellations_last_90_days=view.cancellations_last_90_days,
    )
