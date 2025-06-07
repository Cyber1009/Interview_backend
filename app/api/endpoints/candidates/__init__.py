"""
Candidates domain package.
Contains endpoints for token verification, session management, and recording upload.
Batch processing is now automatic via session completion.
"""
from .router import router
from .recordings import recordings_router
from .sessions import router as sessions_router

# Export the routers for cleaner imports
__all__ = ["router", "recordings_router", "sessions_router"]