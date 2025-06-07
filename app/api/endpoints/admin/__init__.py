"""
Admin endpoints package.
Provides administration functionality including user management, system settings, and monitoring.
"""
from fastapi import APIRouter

# Import directly from the admin.py file
from app.api.endpoints.admin.admin import router as admin_router

# Create combined router
router = APIRouter()

# Include the consolidated admin endpoints with appropriate prefix
router.include_router(admin_router, prefix="")

__all__ = ["router"]