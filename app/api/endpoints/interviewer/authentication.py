"""
Authentication endpoints for login, token refresh, and password management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any
import logging
from datetime import timedelta

# Import from consolidated dependencies module
from app.api.dependencies import (
    db_dependency,
    get_current_user,
    active_user_dependency
)

# Import from consolidated schema structure
from app.schemas.auth_schemas import AuthToken, UserResponse, PasswordChange, UserProfile

# Import from consolidated services
from app.core.security.auth import authenticate_user, get_password_hash, verify_password, create_access_token
from app.core.database.models import User
from app.core.config import settings
from app.api.exceptions import bad_request

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.post("/login", 
             response_model=AuthToken,
             summary="User Login",
             description="Authenticate user and generate access token")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = db_dependency
):
    """
    Authenticate a user and return a JWT access token.
    
    This endpoint verifies the username and password combination,
    and if valid, issues a time-limited JWT access token for the user.
    
    The access token can then be used to authenticate requests to protected endpoints.
    
    Parameters:
    - **username**: User's username
    - **password**: User's password
    
    Returns:
    - **access_token**: JWT token for authentication
    - **token_type**: Type of token (bearer)
    
    Raises:
    - HTTP 401: Invalid credentials
    - HTTP 403: Account inactive
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check subscription status here to provide appropriate error messages
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive. Please contact support."
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/password", 
             response_model=UserResponse,
             summary="Change Password",
             description="Update the password for the currently authenticated user")
def change_password(
    password_change: PasswordChange,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """
    Change the current user's password.
    
    This endpoint allows users to update their password. It requires:
    1. The current password for verification
    2. A new password that meets security requirements
    
    Parameters:
    - **current_password**: User's current password
    - **new_password**: New password to set
    
    Returns:
    - Updated user profile
    
    Raises:
    - HTTP 400: Current password is incorrect or new password is invalid
    """
    # Verify current password
    if not verify_password(password_change.current_password, current_user.hashed_password):
        bad_request("Current password is incorrect")
    
    # Validate new password (you may want to add more validation rules)
    if len(password_change.new_password) < 8:
        bad_request("New password must be at least 8 characters long")
    
    # Update password
    current_user.hashed_password = get_password_hash(password_change.new_password)
    
    # Save changes
    db.commit()
    db.refresh(current_user)
    
    return current_user