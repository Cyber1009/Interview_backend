"""
Main router for the candidates domain.
Combines all candidate-related endpoints into a single router.
"""
from fastapi import APIRouter
from .sessions import router as sessions_router
from .recordings import recordings_router

# Create the main router for candidates domain
router = APIRouter()

# Include session endpoints directly (they already have /interviews/ prefix)
router.include_router(sessions_router, tags=["Candidate Portal"])

# Include recordings endpoints with /interviews/ prefix for consistency
router.include_router(recordings_router, prefix="/interviews/recordings", tags=["Candidate Portal"])

# Note: Batch processing is now automatic via complete-session endpoint
# Manual batch endpoints have been removed to maintain proper application flow

# For backward compatibility
__all__ = ["router"]
