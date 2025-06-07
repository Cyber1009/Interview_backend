"""
Authentication endpoints for login, token refresh, and password management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta

from app.api.dependencies import db_dependency, active_user_dependency
from app.core.security.auth import authenticate_user, create_access_token, get_password_hash, verify_password
from app.core.database.models import User
from app.schemas.auth_schemas import AuthToken as Token, UserResponse, PasswordChange
from app.api.exceptions import not_found, forbidden, bad_request
from app.utils.subscription_utils import update_subscription_status
from app.core.config import settings

# Create router
auth_router = APIRouter()

@auth_router.post("/login", 
                response_model=Token,
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

@auth_router.get("/me", 
               response_model=UserResponse,
               summary="Current User Profile",
               description="Get profile information for the currently authenticated user")
def read_users_me(
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """
    Get current authenticated user's profile information.
    
    This endpoint returns the profile information for the currently authenticated user,
    including their subscription status, account details, and preferences.
    
    It automatically updates the subscription status based on the current date
    and subscription end date before returning the user profile.
    
    Returns:
    - Complete user profile with up-to-date subscription status
    """
    # Re-fetch the user from the database to get the most up-to-date information
    fresh_user_data = db.query(User).filter(User.id == current_user.id).first()
    
    # If for some reason we can't find the user (very unlikely), fall back to current_user
    if not fresh_user_data:
        return current_user
    
    # Update subscription status if needed
    update_subscription_status(fresh_user_data, db)
    
    return fresh_user_data

@auth_router.post("/password", 
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