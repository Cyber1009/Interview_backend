"""
Interviewer domain package.
Contains endpoints for interview creation, management, and analysis.
"""
# Import the consolidated router
from app.api.endpoints.interviewer.router import router

# For backward compatibility, also import individual routers
from app.api.endpoints.interviewer.interviews import router as interviews_router
from app.api.endpoints.interviewer.profile import router as profile_router
from app.api.endpoints.interviewer.results import router as results_router
from app.api.endpoints.interviewer.analytics import router as analytics_router
from app.api.endpoints.interviewer.settings import router as settings_router, theme_router

# Export everything for explicit imports
__all__ = [
    # Main consolidated router
    "router",
    
    # Individual routers for backward compatibility
    "interviews_router",
    "profile_router",
    "results_router",
    "analytics_router",
    "settings_router",
    "theme_router"
]