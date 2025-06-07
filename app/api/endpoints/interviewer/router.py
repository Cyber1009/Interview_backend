"""
Consolidated router for interviewer endpoints.
This file organizes all interviewer-related endpoints into a single, structured router.
"""
from fastapi import APIRouter

from app.api.endpoints.interviewer.interviews import router as interviews_router
from app.api.endpoints.interviewer.profile import router as profile_router
from app.api.endpoints.interviewer.results import router as results_router
from app.api.endpoints.interviewer.analytics import router as analytics_router
from app.api.endpoints.interviewer.settings import router as settings_router
# Remove the theme_router import since it's redundant (it's just an alias for settings_router)

# Main consolidated router that includes all interviewer endpoints
router = APIRouter()

# Include all routers with clean, consistent paths
# The interviews router already has all proper "/interviews/" prefixes
router.include_router(interviews_router)

# Include results router with proper prefix - now includes batch processing capabilities
router.include_router(results_router, prefix="/interviews/{interview_key}/results")

# Include other routers with simple prefixes
router.include_router(profile_router, prefix="/profile")
router.include_router(analytics_router, prefix="/analytics")
# Remove redundant theme_router inclusion - theme endpoints will be accessed via /settings/theme
router.include_router(settings_router, prefix="/settings")