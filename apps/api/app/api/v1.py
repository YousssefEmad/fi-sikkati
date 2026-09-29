"""``/api/v1`` router: one include per domain module (api.md §4)."""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.platform.router import router as platform_router

API_V1_PREFIX = "/api/v1"

router = APIRouter(prefix=API_V1_PREFIX)
router.include_router(platform_router)
