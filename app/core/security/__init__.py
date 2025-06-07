"""
Security module for authentication, authorization and password handling.
"""
from app.core.security.auth import (
    verify_password,
    get_password_hash,
    authenticate_user,
    create_access_token,
    check_subscription_status,
    get_current_user,
    oauth2_scheme,
    # Admin auth functions that were moved from admin_auth.py
    get_current_admin,
    seed_admin_account,
    admin_oauth2_scheme
)

__all__ = [
    # User authentication
    "verify_password",
    "get_password_hash", 
    "authenticate_user", 
    "create_access_token",
    "check_subscription_status", 
    "get_current_user",
    "oauth2_scheme",
    
    # Admin authentication
    "get_current_admin",
    "seed_admin_account",
    "admin_oauth2_scheme"
]
