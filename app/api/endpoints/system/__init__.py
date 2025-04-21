"""
System domain package.
Contains endpoints for system health checks, status monitoring and API information.
"""

from .health import system_router

__all__ = [
    "system_router",
]