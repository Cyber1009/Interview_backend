"""
Admin module for system administration and management.
Consolidated module that combines authentication, account management, system settings, and monitoring.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query, Request, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
from enum import Enum
from sqlalchemy import or_

from app.api.dependencies import db_dependency, admin_dependency
from app.core.database.models import User, PendingAccount, Admin, Question
from app.core.security.auth import create_access_token, get_password_hash, verify_password
from app.schemas.auth_schemas import (
    AdminToken, 
    AdminResponse, 
    AdminCreate,
    AdminUserCreate, 
    AdminUserUpdate,
    UserResponse, 
    AdminActivateAccount
)
from app.schemas.payment_schemas import SubscriptionUpdate
from app.schemas.admin_schemas import (
    SystemConfigUpdate,
    SystemStatusResponse,
    MonitoringMetricsResponse
)
from app.api.exceptions import not_found, forbidden, bad_request
from app.utils.rate_limiter import dynamic_rate_limit
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Create unified router
router = APIRouter()

# ======================================================================
# SECTION: Admin Authentication
# ======================================================================

@router.post("/auth/login", 
             response_model=AdminToken,
             summary="Admin Login",
             description="Authenticate admin and generate access token")
@dynamic_rate_limit(limit_type="auth")
async def admin_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = db_dependency
):
    """
    Authenticate an admin and return a JWT access token.
    
    This endpoint verifies the admin username and password combination,
    and if valid, issues a time-limited JWT access token with admin privileges.
    
    The access token can then be used to authenticate requests to admin-protected endpoints.
    
    Parameters:
    - **username**: Admin username
    - **password**: Admin password
    
    Returns:
    - **access_token**: JWT token for authentication
    - **token_type**: Type of token (bearer)
    - **admin_id**: ID of the authenticated admin
    - **username**: Username of the authenticated admin
    
    Raises:
    - HTTP 401: Invalid credentials
    - HTTP 403: Admin account inactive
    """
    # Check if admin exists and password is correct
    admin = db.query(Admin).filter(Admin.username == form_data.username).first()
    
    if not admin or not verify_password(form_data.password, admin.hashed_password):
        logger.warning(f"Failed admin login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if admin account is active
    if not admin.is_active:
        logger.warning(f"Login attempt with inactive admin account: {admin.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive. Please contact the system administrator."
        )
    
    # Generate token with admin-specific claims
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": admin.username, "is_admin": True, "admin_id": admin.id}, 
        expires_delta=access_token_expires
    )
    
    logger.info(f"Admin login successful: {admin.username}")
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "admin_id": admin.id,
        "username": admin.username
    }

@router.post("/auth/change-password", 
             response_model=dict,
             summary="Change Admin Password",
             description="Change the password for the current admin account")
async def change_admin_password(
    password_change: dict = Body(..., example={"current_password": "oldpass", "new_password": "newpass"}),
    db: Session = db_dependency,
    admin: Admin = admin_dependency
):
    """
    Change the password for the currently authenticated admin.
    
    This endpoint allows admins to update their password when needed.
    Requires authentication and the current password.
    
    Parameters:
    - **current_password**: Current admin password for verification
    - **new_password**: New password to set
    
    Returns:
    - Success message
    
    Raises:
    - HTTP 401: Current password is incorrect
    - HTTP 400: New password doesn't meet requirements
    """
    # Verify current password
    if not verify_password(password_change["current_password"], admin.hashed_password):
        logger.warning(f"Failed password change attempt for admin: {admin.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if len(password_change["new_password"]) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long"
        )
    
    # Update password
    admin.hashed_password = get_password_hash(password_change["new_password"])
    db.commit()
    
    logger.info(f"Password changed successfully for admin: {admin.username}")
    return {"message": "Password changed successfully"}

# Admin creation endpoint removed for security reasons
# @router.post("/auth/create", 
#             response_model=AdminResponse,
#             summary="Create Admin Account",
#             description="Create a new admin account (first admin or super admin only)")
# async def create_admin(
#    admin_data: AdminCreate,
#    db: Session = db_dependency
# ):
#    """
#    Create a new admin account.
#    
#    This special endpoint is used in two scenarios:
#    1. Creating the first admin account in the system
#    2. Creating additional admin accounts by an existing admin
#    
#    The first admin account can be created without authentication.
#    Additional admin accounts require admin authentication.
#    
#    Parameters:
#    - **username**: Admin username
#    - **password**: Admin password
#    - **email**: Admin email
#    - **full_name**: Admin full name (optional)
#    
#    Returns:
#    - The newly created admin account details
#    
#    Raises:
#    - HTTP 400: Username or email already in use
#    - HTTP 403: Not authorized to create admin accounts
#    """
#    # Check if this is the first admin account
#    admin_count = db.query(Admin).count()
#    is_first_admin = admin_count == 0
#    
#    # Check if username already exists
#    existing_admin = db.query(Admin).filter(Admin.username == admin_data.username).first()
#    if existing_admin:
#        bad_request("Username already in use")
#    
#    # Check if email already exists
#    email_exists = db.query(Admin).filter(Admin.email == admin_data.email).first()
#    if email_exists:
#        bad_request("Email already in use")
#    
#    # Create new admin
#    hashed_password = get_password_hash(admin_data.password)
#    new_admin = Admin(
#        username=admin_data.username,
#        hashed_password=hashed_password,
#        email=admin_data.email,
#        full_name=admin_data.full_name,
#        is_active=True
#    )
#    
#    db.add(new_admin)
#    db.commit()
#    db.refresh(new_admin)
#    
#    if is_first_admin:
#        logger.info(f"First admin account created: {new_admin.username}")
#    else:
#        logger.info(f"Additional admin account created: {new_admin.username}")
#    
#    return new_admin

# ======================================================================
# SECTION: User Account Management
# ======================================================================

# Define enum for sort fields
class SortField(str, Enum):
    id = "id"
    username = "username"
    created_at = "created_at"
    subscription_end_date = "subscription_end_date"

# Create a specific response model for pending accounts
class PendingAccountsResponse(BaseModel):
    """Response model for pending accounts endpoint that properly handles empty lists"""
    accounts: List[UserResponse] = []
    
    class Config:
        from_attributes = True

# ======================================================================
# SECTION: Pending Account Management
# ======================================================================

@router.get("/users/pending", 
                   response_model=PendingAccountsResponse,
                   summary="List Pending Accounts",
                   description="View all user accounts that have registered but not completed activation")
def get_pending_accounts(
    db: Session = db_dependency,
    _: Admin = admin_dependency
):
    """
    List all pending (unactivated) accounts.
    
    This endpoint retrieves accounts that have been registered but have not yet
    completed the activation process (typically payment/subscription setup).
    
    These accounts are stored in a separate table until activation is complete.
    
    Returns:
    - List of pending user accounts (may be empty if no pending accounts exist)
    """
    pending = db.query(PendingAccount).all()
    
    # Convert to response format
    results = []
    
    # Process pending accounts if they exist
    for account in pending:
        results.append(UserResponse(
            id=account.id,
            username=account.username,
            email=account.email,
            company=account.company,
            is_active=False,
            subscription_status="pending",
            created_at=account.created_at,
            # Add expiration as subscription_end_date for display purposes
            subscription_end_date=account.expiration_date
        ))
    
    # Return using the wrapper model
    return PendingAccountsResponse(accounts=results)

@router.post("/users/pending/{account_id}/activate", 
                   response_model=UserResponse,
                   summary="Activate Pending Account",
                   description="Manually activate a pending account with subscription details")
def activate_pending_account(
    account_id: int,
    activation: AdminActivateAccount,
    db: Session = db_dependency,
    _: Admin = admin_dependency
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
        company=pending_account.company,
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

@router.delete("/users/pending/{account_id}", 
                      status_code=status.HTTP_204_NO_CONTENT,
                      summary="Delete Pending Account",
                      description="Remove a pending registration that has not been activated")
def delete_pending_account(
    account_id: int,
    db: Session = db_dependency,
    _: Admin = admin_dependency
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

@router.get("/users", 
                   response_model=List[UserResponse],
                   summary="List All User Accounts",
                   description="Get a list of all user accounts with filtering and sorting options")
def get_all_accounts(
    status: Optional[str] = Query(None, description="Filter by subscription status: active, expired, inactive, trial"),
    search: Optional[str] = Query(None, description="Search users by username or email"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    created_after: Optional[datetime] = Query(None, description="Filter users created after this date"),
    created_before: Optional[datetime] = Query(None, description="Filter users created before this date"),
    sort_by: Optional[SortField] = Query(SortField.id, description="Field to sort by"),
    sort_order: Optional[str] = Query("asc", description="Sort order (asc or desc)"),
    limit: Optional[int] = Query(100, description="Maximum number of results to return", ge=1, le=1000),
    offset: Optional[int] = Query(0, description="Number of results to skip for pagination", ge=0),
    db: Session = db_dependency,
    _: Admin = admin_dependency
):
    """
    List all user accounts with extensive filtering and sorting options.
    
    Administrators can view all registered users with flexible options for:
    - Filtering by status, company, creation date
    - Searching by username or email
    - Sorting by various fields
    - Pagination for large result sets
    
    Parameters:
    - **status** (optional): Filter users by subscription status
      - active: Currently active subscriptions
      - expired: Subscriptions that have expired
      - inactive: Manually deactivated accounts
      - trial: Users in trial period
    - **search** (optional): Search term for username or email
    - **company** (optional): Filter by company name
    - **created_after** (optional): Show users created after date
    - **created_before** (optional): Show users created before date
    - **sort_by** (optional): Field to sort results by
    - **sort_order** (optional): Sort order (asc/desc)
    - **limit** (optional): Maximum number of results (pagination)
    - **offset** (optional): Number of results to skip (pagination)
    
    Returns:
    - List of user accounts matching the filter criteria
    """
    # Start with base query
    query = db.query(User)
    
    # Apply filters if provided
    if status:
        query = query.filter(User.subscription_status == status)
        
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.username.ilike(search_term)) | 
            (User.email.ilike(search_term))
        )
        
    if company:
        company_term = f"%{company}%"
        query = query.filter(User.company.ilike(company_term))
        
    if created_after:
        query = query.filter(User.created_at >= created_after)
        
    if created_before:
        query = query.filter(User.created_at <= created_before)
    
    # Apply sorting
    sort_column = getattr(User, sort_by.value)
    if sort_order.lower() == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    # Execute query
    users = query.all()
    return users

@router.get("/users/{user_id}", 
                   response_model=UserResponse,
                   summary="Get User Account Details",
                   description="Get detailed information about a specific user account")
def get_account_details(
    user_id: int,
    db: Session = db_dependency,
    _: Admin = admin_dependency
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

@router.post("/users", 
                    response_model=UserResponse,
                    summary="Create User Account",
                    description="Administrators can create new user accounts directly")
def create_user(
    user: AdminUserCreate,
    db: Session = db_dependency,
    _: Admin = admin_dependency
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

@router.put("/users/{user_id}", 
                   response_model=UserResponse,
                   summary="Update User Account",
                   description="Update a user's account information and subscription status")
def update_user_account(
    user_id: int, 
    user_data: AdminUserUpdate, 
    db: Session = db_dependency,
    _: Admin = admin_dependency
):
    """
    Update a user's account details and subscription information.
    
    This endpoint allows administrators to:
    - Change basic user information (username, email, company)
    - Control account access (is_active)
    - Manage subscription details (plan, end date, status)
    
    The system enforces logical consistency between fields:
    - If a subscription is provided with future end date, status is set to "active"
    - If a subscription is provided with past end date, status is set to "expired"
    - If account is manually deactivated, subscription status is updated accordingly
    
    Parameters:
    - **user_id**: ID of the user account to update
    - **user_data**: User account fields to update
    
    Returns:
    - Updated user account information
    
    Raises:
    - HTTP 404: User not found
    - HTTP 400: Inconsistent subscription data
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user fields from request data
    for field, value in user_data.dict(exclude_unset=True, exclude_none=True).items():
        setattr(user, field, value)
    
    # Enforce logical consistency between subscription fields
    now = datetime.now()
    
    # If subscription end date is provided, check if it's in the future
    if user_data.subscription_end_date is not None:
        if user_data.subscription_end_date > now:
            # Future date: subscription should be active
            if user_data.subscription_status is None:
                user.subscription_status = "active"
        else:
            # Past date: subscription should be expired
            if user_data.subscription_status is None:
                user.subscription_status = "expired"
    
    # If account is explicitly deactivated, update subscription status
    if user_data.is_active is False and user_data.subscription_status is None:
        # Don't change "expired" status
        if user.subscription_status not in ["expired"]:
            user.subscription_status = "suspended"
    
    # If account is explicitly activated with an active subscription plan but expired date,
    # warn about this inconsistency
    if (user_data.is_active is True and 
        user.subscription_end_date and 
        user.subscription_end_date < now):
        logger.warning(
            f"Admin activated user {user.username} with expired subscription " + 
            f"(end date: {user.subscription_end_date}). This account may be " + 
            "automatically deactivated by the subscription sync job."
        )
    
    db.commit()
    db.refresh(user)
    
    return user

@router.delete("/users/{user_id}", 
                      status_code=status.HTTP_204_NO_CONTENT,
                      summary="Delete User Account",
                      description="Permanently delete a user account and all associated data")
def delete_account(
    user_id: int,
    db: Session = db_dependency,
    _: Admin = admin_dependency
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

# ======================================================================
# SECTION: System Management
# ======================================================================

@router.get("/system/status", 
          response_model=SystemStatusResponse,
          summary="System Status",
          description="Get overall system status and health information")
def get_system_status(
    db: Session = db_dependency,
    _: Admin = admin_dependency
):
    """
    Get current system status and health metrics.
    
    This endpoint provides an overview of the system's health and performance,
    including database connection status, storage availability, and other key metrics.
    
    Returns:
    - Current system status and metrics including real-time checks
    """
    from app.services.monitoring.health_check_service import HealthCheckService
    
    # Use our health check service to get real system status
    status_data = HealthCheckService.get_full_status(db)
    
    # Format the response according to SystemStatusResponse schema
    status = {
        "status": status_data["status"],
        "database": status_data["database"],
        "storage": status_data["storage"],
        "processors": status_data["processors"],
        "uptime": status_data["uptime"],
        "version": status_data["version"]
    }
    
    return status

# Add a utility endpoint to fix interviews with invalid questions
@router.post("/system/fix-invalid-questions", 
             response_model=Dict[str, Any],
             summary="Fix interviews with invalid questions",
             description="Updates all questions with invalid timer values (<=0) to use default values")
async def fix_invalid_questions(
    min_preparation_time: float = 30.0,
    min_responding_time: float = 60.0,
    db: Session = db_dependency,
    current_admin: Admin = admin_dependency
):
    """
    Administrative utility to fix all questions with invalid timer values.
    
    This endpoint:
    1. Finds all questions with preparation_time or responding_time <= 0
    2. Updates them to use the specified minimum values
    3. Returns a summary of changes made
    """
    # Find all questions with invalid timer values
    invalid_questions = db.query(Question).filter(
        or_(
            Question.preparation_time <= 0,
            Question.responding_time <= 0
        )
    ).all()
    
    if not invalid_questions:
        return {
            "status": "success",
            "message": "No invalid questions found",
            "updated_count": 0,
            "details": []
        }
    
    # Keep track of changes for reporting
    updated_count = 0
    update_details = []
    
    # Update each invalid question
    for question in invalid_questions:
        question_info = {
            "id": question.id,
            "interview_id": question.interview_id,
            "old_values": {
                "preparation_time": question.preparation_time,
                "responding_time": question.responding_time
            },
            "new_values": {}
        }
        
        # Fix preparation_time if needed
        if question.preparation_time <= 0:
            question.preparation_time = min_preparation_time
            question_info["new_values"]["preparation_time"] = min_preparation_time
            
        # Fix responding_time if needed
        if question.responding_time <= 0:
            question.responding_time = min_responding_time
            question_info["new_values"]["responding_time"] = min_responding_time
            
        updated_count += 1
        update_details.append(question_info)
    
    # Commit the changes
    db.commit()
    
    return {
        "status": "success",
        "message": f"Fixed {updated_count} questions with invalid timer values",
        "updated_count": updated_count,
        "details": update_details
    }