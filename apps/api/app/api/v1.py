"""``/api/v1`` router: one include per domain module (api.md §4)."""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.admin.router import analytics_router as admin_analytics_router
from app.modules.admin.router import audit_router as admin_audit_router
from app.modules.admin.router import flags_router as admin_flags_router
from app.modules.admin.router import reports_router as admin_reports_router
from app.modules.admin.router import settings_router as admin_settings_router
from app.modules.admin.router import trips_router as admin_trips_router
from app.modules.admin.router import users_router as admin_users_router
from app.modules.ai.router import router as ai_router
from app.modules.auth.router import phone_router
from app.modules.auth.router import router as auth_router
from app.modules.auth.router import sessions_router as auth_sessions_router
from app.modules.bookings.router import join_router, me_join_router, trip_join_router
from app.modules.chat.router import me_router as me_conversations_router
from app.modules.chat.router import router as conversations_router
from app.modules.maps.router import router as maps_router
from app.modules.notifications.router import preferences_router as notification_preferences_router
from app.modules.notifications.router import push_router
from app.modules.notifications.router import router as notifications_router
from app.modules.platform.router import router as platform_router
from app.modules.pricing.router import router as pricing_router
from app.modules.safety.router import (
    me_blocks_router,
    me_reports_router,
    ratings_router,
    reports_router,
)
from app.modules.search.router import router as search_router
from app.modules.trips.router import me_trips_router, trips_router
from app.modules.users.router import me_router, users_router
from app.modules.vehicles.router import admin_router as admin_vehicles_router
from app.modules.vehicles.router import me_router as vehicles_router
from app.modules.verification.router import admin_router as admin_verifications_router
from app.modules.verification.router import me_router as verification_router

API_V1_PREFIX = "/api/v1"

router = APIRouter(prefix=API_V1_PREFIX)
router.include_router(platform_router)
router.include_router(auth_router)
router.include_router(phone_router)
# ``/me/sessions`` before ``/me`` so the more specific prefix is matched first.
router.include_router(auth_sessions_router)
router.include_router(verification_router)
router.include_router(vehicles_router)
router.include_router(maps_router)
router.include_router(pricing_router)
router.include_router(trips_router)
router.include_router(trip_join_router)
router.include_router(me_trips_router)
router.include_router(me_join_router)
router.include_router(join_router)
router.include_router(search_router)
router.include_router(me_conversations_router)
router.include_router(conversations_router)
router.include_router(notifications_router)
router.include_router(notification_preferences_router)
router.include_router(push_router)
router.include_router(ratings_router)
router.include_router(reports_router)
router.include_router(me_reports_router)
router.include_router(me_blocks_router)
router.include_router(me_router)
router.include_router(users_router)
router.include_router(admin_verifications_router)
router.include_router(admin_vehicles_router)
router.include_router(admin_users_router)
router.include_router(admin_trips_router)
router.include_router(admin_reports_router)
router.include_router(admin_analytics_router)
router.include_router(admin_settings_router)
router.include_router(admin_flags_router)
router.include_router(admin_audit_router)
router.include_router(ai_router)
