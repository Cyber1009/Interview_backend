"""
Endpoints for user registration and account setup.
"""
from fastapi import APIRouter, Depends, status, HTTPException, Response
from fastapi.responses import JSONResponse, RedirectResponse
import logging
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import stripe
import os
import uuid
from datetime import datetime, timezone, timedelta

from app.core.database.models import PendingAccount, User
from app.schemas.auth_schemas import RegistrationCreate, RegistrationResponse
from app.schemas.payment_schemas import RegistrationCheckout, RegistrationComplete, CheckoutSession
from app.core.config import settings
from app.api.dependencies import db_dependency
from app.api.exceptions import not_found, bad_request, payment_error
from app.core.security.auth import get_password_hash
from app.utils.subscription_utils import process_registration_completion
from app.utils.rate_limiter import dynamic_rate_limit, RateLimitType

# Create router with standardized naming
router = APIRouter()

@router.post("/", 
           response_model=RegistrationResponse,
           summary="Register New Account",
           description="Create a new pending account that requires activation")
@dynamic_rate_limit(limit_type=RateLimitType.REGISTRATION)
async def register_new_account(
    registration: RegistrationCreate,
    db: Session = db_dependency
):
    """
    Register a new account (first step in registration flow).
    
    This endpoint creates a pending account record that must be activated
    through the subscription and payment process. The account remains in a 
    pending state until checkout is completed successfully.
    
    Registration flow:
    1. Register account (this endpoint) → returns verification token
    2. Select subscription plan and process payment (via /payments/checkout/registration/{plan_id})
    3. Complete registration after successful payment (via /payments/checkout/registration/complete)
    
    Parameters:
    - **registration**: User registration details including username, password, email, etc.
    
    Returns:
    - Registration information including verification token needed for subscription checkout
    
    Raises:
    - HTTP 400: Username or email already registered
    """
    # Check if username already exists
    exists = db.query(User).filter(User.username == registration.username).first()
    if exists:
        bad_request("Username already registered")
    
    # Check if email already exists
    if registration.email:
        email_exists = db.query(User).filter(User.email == registration.email).first()
        if email_exists:
            bad_request("Email already registered")
    
    # Hash the password
    hashed_password = get_password_hash(registration.password)
    
    # Set expiration date for verification token (48 hours)
    expiration_date = datetime.now(timezone.utc) + timedelta(hours=48)
    
    # Generate a verification token
    verification_token = str(uuid.uuid4())
    
    # Create pending account
    pending_account = PendingAccount(
        username=registration.username,
        hashed_password=hashed_password,
        email=registration.email,
        company=registration.company,
        expiration_date=expiration_date,
        verification_token=verification_token
    )
    
    db.add(pending_account)
    db.commit()
    db.refresh(pending_account)
    
    return RegistrationResponse(
        username=pending_account.username,
        email=pending_account.email,
        verification_token=pending_account.verification_token,
        expiration_date=pending_account.expiration_date
    )

@router.post("/activate", 
         response_model=Dict[str, Any],
         summary="Activate or Reactivate Account",
         description="Activate a pending account or reactivate an expired account")
@dynamic_rate_limit(limit_type=RateLimitType.REGISTRATION)
async def activate_account(
    activation: RegistrationComplete,
    db: Session = db_dependency
):
    """
    Unified endpoint to activate a new account or reactivate an expired account.
    
    This endpoint handles multiple scenarios:
    1. First-time activation of a pending account
    2. Reactivation of an expired account
    3. Subscription renewal after payment
    
    The endpoint automatically detects whether the provided token is for a pending account
    (new registration) or is associated with an existing account (reactivation).
    
    Parameters:
    - **activation**: Contains verification token, and optional subscription and payment details
    
    Returns:
    - Account activation status and user information
    
    Raises:
    - HTTP 400: Invalid or expired token
    - HTTP 404: Account not found
    """
    # Check for pending account first (new activation)
    pending_account = db.query(PendingAccount).filter(
        PendingAccount.verification_token == activation.verification_token
    ).first()
    
    if pending_account:
        # Handle new account activation
        user, success = process_registration_completion(
            db=db,
            verification_token=activation.verification_token,
            subscription_id=activation.subscription_id,
            customer_id=activation.customer_id,
            plan_id=activation.plan_id,
            subscription_status="active",
            subscription_end_date=activation.subscription_end_date
        )
        
        if not success or not user:
            bad_request("Failed to activate account with the provided token")
            
        return {
            "status": "activated",
            "message": "Account successfully activated",
            "account_type": "new",
            "username": user.username,
            "is_active": user.is_active,
            "subscription_status": user.subscription_status,
            "subscription_end_date": user.subscription_end_date
        }
    
    # If no pending account found, check for existing account reactivation
    user = db.query(User).filter(
        User.reactivation_token == activation.verification_token
    ).first()
    
    if not user:
        not_found("No pending or existing account found with provided token")
    
    # Update existing account with new subscription info
    try:
        user.is_active = True
        user.subscription_status = "active"
        user.subscription_id = activation.subscription_id
        user.payment_method_id = activation.customer_id
        
        if activation.subscription_end_date:
            user.subscription_end_date = activation.subscription_end_date
        
        # Clear reactivation token after use
        user.reactivation_token = None
        
        db.commit()
        
        return {
            "status": "reactivated",
            "message": "Account successfully reactivated",
            "account_type": "existing",
            "username": user.username,
            "is_active": user.is_active,
            "subscription_status": user.subscription_status,
            "subscription_end_date": user.subscription_end_date
        }
    except Exception as e:
        db.rollback()
        bad_request(f"Failed to reactivate account: {str(e)}")

@router.post("/generate-reactivation", 
          response_model=Dict[str, Any],
          summary="Generate Reactivation Token",
          description="Generate a reactivation token for an expired account")
@dynamic_rate_limit(limit_type=RateLimitType.REGISTRATION)
async def generate_reactivation_token(
    username: str,
    db: Session = db_dependency
):
    """
    Generate a new reactivation token for an expired account.
    
    This endpoint creates a token that can be used with the /activate endpoint
    to reactivate an expired account after renewal payment.
    
    Parameters:
    - **username**: The username of the expired account
    
    Returns:
    - Reactivation token and expiration date
    
    Raises:
    - HTTP 404: Account not found
    - HTTP 400: Account is already active
    """
    # Find the user account
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        not_found("User account not found")
    
    if user.is_active and user.subscription_status == "active":
        bad_request("Account is already active")
    
    # Generate a reactivation token with 48-hour expiration
    reactivation_token = str(uuid.uuid4())
    expiration_date = datetime.now(timezone.utc) + timedelta(hours=48)
    
    user.reactivation_token = reactivation_token
    user.reactivation_expiration = expiration_date
    
    db.commit()
    
    return {
        "username": user.username,
        "reactivation_token": reactivation_token,
        "expiration_date": expiration_date
    }

# For backward compatibility
registration_router = router