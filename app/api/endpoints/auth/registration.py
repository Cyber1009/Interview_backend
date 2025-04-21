"""
Endpoints for user registration and account setup.
"""
from fastapi import APIRouter, Depends, status, HTTPException, Response
from fastapi.responses import JSONResponse, RedirectResponse
import logging
from sqlalchemy.orm import Session
from typing import Optional
import stripe
import os
import uuid
from datetime import datetime, timezone, timedelta

# Updated import path
from app.core.database.models import PendingAccount, User
from app.schemas.auth_schemas import RegistrationCreate, RegistrationResponse
from app.schemas import UserRegistration, RegistrationCheckout, RegistrationComplete, StripeCheckoutResponse
from app.core.config import settings
from app.api.deps import db_dependency
from app.utils.error_utils import not_found, bad_request, payment_error
from app.core.security.auth import get_password_hash

# Create router
registration_router = APIRouter()

@registration_router.post("/", 
                        response_model=RegistrationResponse,
                        summary="Register New Account",
                        description="Create a new pending account that requires activation")
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
        company_name=registration.company_name,
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