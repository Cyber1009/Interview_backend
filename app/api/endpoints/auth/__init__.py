"""
Authentication domain package.
Contains endpoints related to user authentication, login, and registration.
"""

from .auth import auth_router
from .registration import registration_router

__all__ = [
    "auth_router",
    "registration_router",
]