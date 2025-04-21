"""
Admin domain package.
Contains endpoints for system administration and account management.
"""

from .admin import admin_router, get_admin_auth
from .accounts import accounts_router

__all__ = [
    "admin_router",
    "accounts_router",
    "get_admin_auth",
]