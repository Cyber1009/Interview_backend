"""
Admin endpoints for managing user accounts.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
import secrets
from typing import List, Optional
from datetime import datetime

from app.api.deps import db_dependency, admin_dependency
# Updated import path
from app.core.database.models import User, PendingAccount
from app.schemas import AdminUserCreate, UserResponse, SubscriptionUpdate, AdminActivateAccount
from app.security import get_password_hash
from app.api.endpoints.admin.admin import get_admin_auth

# Create router
accounts_router = APIRouter()

@accounts_router.post("/", 
                    response_model=UserResponse,
                    summary="Create User Account",
                    description="Administrators can create new user accounts directly")
def create_user(
    user: AdminUserCreate,
    db: Session = db_dependency,
    _: bool = Depends(get_admin_auth)
):
    """
    Create a new interviewer account (admin use only).
    
    This endpoint allows administrators to create user accounts directly without requiring 
    the standard registration and payment process. This is useful for:
    - Creating test accounts
    - Setting up enterprise customers
    - Troubleshooting account issues
    
    Parameters:
    - **user**: User details including username and password
    
    Returns:
    - Created user details
    
    Raises:
    - HTTP 400: Username already exists
    """
    # Check if username already exists
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Create new user 
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username, 
        hashed_password=hashed_password,
        is_active=True  # Active but without subscription
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@accounts_router.get("/", 
                   response_model=List[UserResponse],
                   summary="List All User Accounts",
                   description="Get a list of all user accounts with optional status filtering")
def get_all_accounts(
    status: Optional[str] = None,
    db: Session = db_dependency,
    _: bool = Depends(get_admin_auth)
):
    """
    List all user accounts with optional status filter.
    
    Administrators can view all registered users and filter by subscription status.
    This provides an overview of the system's users for administrative purposes.
    
    Parameters:
    - **status** (optional): Filter users by subscription status
      - active: Currently active subscriptions
      - expired: Subscriptions that have expired
      - inactive: Manually deactivated accounts
      - trial: Users in trial period
    
    Returns:
    - List of user accounts matching the filter criteria
    """
    query = db.query(User)
    
    # Apply filters if status is provided
    if status:
        query = query.filter(User.subscription_status == status)
    
    # Execute query
    users = query.all()
    return users

@accounts_router.get("/pending", 
                   response_model=List[UserResponse],
                   summary="List Pending Accounts",
                   description="View all user accounts that have registered but not completed activation")
def get_pending_accounts(
    db: Session = db_dependency,
    _: bool = Depends(get_admin_auth)
):
    """
    List all pending (unactivated) accounts.
    
    This endpoint retrieves accounts that have been registered but have not yet
    completed the activation process (typically payment/subscription setup).
    
    These accounts are stored in a separate table until activation is complete.
    
    Returns:
    - List of pending user accounts
    """
    pending = db.query(PendingAccount).all()
    
    # Convert to response format
    results = []
    for account in pending:
        results.append(UserResponse(
            id=account.id,
            username=account.username,
            email=account.email,
            company_name=account.company_name,
            is_active=False,
            subscription_status="pending",
            created_at=account.created_at,
            # Add expiration as subscription_end_date for display purposes
            subscription_end_date=account.expiration_date
        ))
    
    return results

@accounts_router.delete("/pending/{account_id}", 
                      status_code=status.HTTP_204_NO_CONTENT,
                      summary="Delete Pending Account",
                      description="Remove a pending registration that has not been activated")
def delete_pending_account(
    account_id: int,
    db: Session = db_dependency,
    _: bool = Depends(get_admin_auth)
):
    """
    Delete a pending (unactivated) account.
    
    This endpoint removes accounts that have been registered but not yet activated.
    Useful for removing:
    - Abandoned registration attempts
    - Spam registrations
    - Expired registration attempts
    
    Parameters:
    - **account_id**: ID of the pending account to delete
    
    Returns:
    - No content on success
    
    Raises:
    - HTTP 404: Pending account not found
    """
    account = db.query(PendingAccount).filter(PendingAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Pending account not found")
    
    # Delete account
    db.delete(account)
    db.commit()
    
    return None

@accounts_router.post("/pending/{account_id}/activate", 
                   response_model=UserResponse,
                   summary="Activate Pending Account",
                   description="Manually activate a pending account with subscription details")
def activate_pending_account(
    account_id: int,
    activation: AdminActivateAccount,
    db: Session = db_dependency,
    _: bool = Depends(get_admin_auth)
):
    """
    Manually activate a pending account (admin use only).
    
    This endpoint allows administrators to manually convert a pending account
    into an active user account. This is useful for:
    - Handling registration issues
    - Direct user onboarding without payment flow
    - Testing account functionality
    
    Parameters:
    - **account_id**: ID of the pending account to activate
    - **activation**: Subscription details for the new account
    
    Returns:
    - Newly activated user account information
    
    Raises:
    - HTTP 404: Pending account not found
    """
    # Find the pending account
    pending_account = db.query(PendingAccount).filter(PendingAccount.id == account_id).first()
    if not pending_account:
        raise HTTPException(status_code=404, detail="Pending account not found")
    
    # Generate a subscription ID if needed
    subscription_id = f"admin_activated_{account_id}_{int(datetime.now().timestamp())}"
    
    # Create active user from pending account
    new_user = User(
        username=pending_account.username,
        hashed_password=pending_account.hashed_password,
        email=pending_account.email,
        company_name=pending_account.company_name,
        is_active=activation.is_active,
        subscription_id=subscription_id,
        subscription_plan=activation.subscription_plan,
        subscription_end_date=activation.subscription_end_date,
        subscription_status="active" if activation.is_active else "inactive",
    )
    
    # Add the user to the database and remove the pending account
    db.add(new_user)
    db.delete(pending_account)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@accounts_router.get("/{user_id}", 
                   response_model=UserResponse,
                   summary="Get User Account Details",
                   description="Get detailed information about a specific user account")
def get_account_details(
    user_id: int,
    db: Session = db_dependency,
    _: bool = Depends(get_admin_auth)
):
    """
    Get detailed information about a specific user account.
    
    This endpoint retrieves comprehensive details about a user account,
    including subscription status, creation date, and other account metadata.
    
    Parameters:
    - **user_id**: ID of the user account to retrieve
    
    Returns:
    - Detailed user account information
    
    Raises:
    - HTTP 404: User not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@accounts_router.put("/{user_id}", 
                   response_model=UserResponse,
                   summary="Update Account Status",
                   description="Update a user's subscription status and plan manually")
def update_account_status(
    user_id: int, 
    subscription: SubscriptionUpdate, 
    db: Session = db_dependency,
    _: bool = Depends(get_admin_auth)
):
    """
    Update a user's subscription details (for troubleshooting).
    
    This endpoint allows administrators to manually modify subscription details
    when issues occur with the automatic subscription management. Use cases include:
    
    - Extending subscription periods for customer service reasons
    - Fixing issues with payment processing
    - Manually activating or deactivating accounts
    - Changing subscription plans (basic, premium, enterprise)
    
    Parameters:
    - **user_id**: ID of the user account to update
    - **subscription**: New subscription details including end date, active status, and plan
    
    Returns:
    - Updated user account information
    
    Raises:
    - HTTP 404: User not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update subscription details
    user.subscription_end_date = subscription.subscription_end_date
    user.is_active = subscription.is_active
    
    # Update subscription plan if provided
    if subscription.subscription_plan is not None:
        user.subscription_plan = subscription.subscription_plan
    
    if subscription.is_active:
        user.subscription_status = "active"
    else:
        user.subscription_status = "inactive"
    
    db.commit()
    db.refresh(user)
    
    return user

@accounts_router.delete("/{user_id}", 
                      status_code=status.HTTP_204_NO_CONTENT,
                      summary="Delete User Account",
                      description="Permanently delete a user account and all associated data")
def delete_account(
    user_id: int,
    db: Session = db_dependency,
    _: bool = Depends(get_admin_auth)
):
    """
    Delete a user account (admin use only).
    
    This endpoint permanently removes a user account and all associated data.
    This is intended for:
    - GDPR compliance requests
    - Data cleanup for dormant accounts
    - Removing test accounts
    
    Note: This is a destructive operation and cannot be undone.
    
    Parameters:
    - **user_id**: ID of the user account to delete
    
    Returns:
    - No content on success
    
    Raises:
    - HTTP 404: User not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete user
    db.delete(user)
    db.commit()
    
    return None