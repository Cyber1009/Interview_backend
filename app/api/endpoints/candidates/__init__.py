"""
Candidates domain package.
Contains endpoints for candidate session management and recording submission.
"""

from .verification import verification_router
from .sessions import sessions_router
from .recordings import recordings_router

# Legacy import kept for backward compatibility - this can be removed when router.py is updated
from .candidates import candidates_router

__all__ = [
    "verification_router",
    "sessions_router",
    "recordings_router",
    "candidates_router",  # Legacy router, maintained for backward compatibility
]