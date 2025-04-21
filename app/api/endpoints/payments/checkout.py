"""
Endpoints for payment checkout and subscription management.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging
from typing import Dict, Optional, List, Any
import stripe
import os
from datetime import datetime, timedelta, timezone

# Updated import path
from app.core.database.models import User, PendingAccount
from app.schemas import (
    CheckoutSession, CustomerPortalSession, SubscriptionPlanList, 
    SubscriptionPlan, UserResponse, RegistrationResponse,
    RegistrationComplete  # Make sure RegistrationComplete is imported
)
from app.core.config import settings
from app.utils.error_utils import not_found, bad_request, internal_error
from app.api.deps import db_dependency, active_user_dependency

# Configure logger
logger = logging.getLogger(__name__)

# Configure Stripe API key
stripe.api_key = settings.STRIPE_API_KEY

# Configure subscription plans
SUBSCRIPTION_PLANS = {
    "basic": {
        "name": "Basic Plan",
        "price_id": settings.STRIPE_BASIC_PRICE_ID,
        "duration": "monthly",
        "duration_days": 30,
        "features": [
            "Interview up to 10 candidates per month",
            "1 interview template",
            "Basic analytics",
            "Email support"
        ]
    },
    "premium": {
        "name": "Premium Plan",
        "price_id": settings.STRIPE_PREMIUM_PRICE_ID,
        "duration": "monthly",
        "duration_days": 30,
        "features": [
            "Interview up to 50 candidates per month",
            "5 interview templates",
            "Advanced analytics",
            "Priority support",
            "Custom branding"
        ]
    },
    "enterprise": {
        "name": "Enterprise Plan",
        "price_id": settings.STRIPE_ENTERPRISE_PRICE_ID,
        "duration": "yearly",
        "duration_days": 365,
        "features": [
            "Unlimited candidates",
            "Unlimited templates",
            "Advanced analytics and reporting",
            "Dedicated support",
            "Custom branding",
            "API access"
        ]
    }
}

# Create router
checkout_router = APIRouter()

@checkout_router.get("/plans", response_model=SubscriptionPlanList)
async def get_subscription_plans():
    """Get all available subscription plans"""
    return SubscriptionPlanList(
        basic=SubscriptionPlan(**SUBSCRIPTION_PLANS["basic"]),
        premium=SubscriptionPlan(**SUBSCRIPTION_PLANS["premium"]),
        enterprise=SubscriptionPlan(**SUBSCRIPTION_PLANS["enterprise"])
    )

@checkout_router.post("/customer-portal", response_model=CustomerPortalSession)
async def create_customer_portal_session(
    current_user: User = active_user_dependency,
    db: Session = db_dependency
):
    """
    Create a Stripe Customer Portal session for the current user.
    
    This allows users to manage their subscription (update payment method,
    cancel subscription, etc.)
    """
    if not current_user.payment_method_id:
        bad_request("No payment method found")
    
    # Create a portal session
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.payment_method_id,
            return_url=f"{settings.FRONTEND_URL}/account"
        )
    except Exception as e:
        logger.error(f"Error creating portal session: {str(e)}")
        internal_error(f"Error creating customer portal: {str(e)}")
    
    return CustomerPortalSession(portal_url=portal_session.url)

@checkout_router.post("/reactivate-subscription/{plan_id}", response_model=CheckoutSession)
async def reactivate_subscription(
    plan_id: str,
    current_user: User = active_user_dependency,
    db: Session = db_dependency
):
    """
    Reactivate an expired subscription.
    
    This endpoint is used when a user with an expired subscription
    wants to reactive their account.
    """
    # Verify the user's subscription is expired
    if current_user.is_active and current_user.subscription_status == "active":
        bad_request("Subscription is already active")
    
    # Get the price ID for the selected plan
    if plan_id not in SUBSCRIPTION_PLANS:
        not_found("Plan", plan_id)
        
    price_id = SUBSCRIPTION_PLANS[plan_id]["price_id"]
    
    # Create a checkout session
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=f"{settings.FRONTEND_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/subscription/cancel",
            client_reference_id=current_user.id,
            customer_email=current_user.email,
            metadata={
                "user_id": current_user.id,
                "plan_id": plan_id,
                "action": "reactivate"
            }
        )
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        internal_error(f"Error creating checkout session: {str(e)}")
    
    return CheckoutSession(
        checkout_url=checkout_session.url,
        session_id=checkout_session.id
    )

# IMPORTANT: Define the more specific path (/registration/complete) BEFORE the general path (/registration/{plan_id})
@checkout_router.post("/registration/complete", response_model=UserResponse)
async def complete_registration(
    session_id: str = Query(..., description="Stripe checkout session ID"),
    token: Optional[str] = Query(None, description="Verification token (optional if stored in session metadata)"),
    db: Session = db_dependency
):
    """
    Complete the signup process after successful payment.
    
    This endpoint is called after the user completes the Stripe checkout.
    It converts the pending account to an active user account.
    
    Parameters:
    - **session_id**: Stripe checkout session ID (passed as query parameter)
    - **token**: Optional verification token (if not provided, will try to get it from session metadata)
    
    Returns:
    - Full user details for the newly created account
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Retrieve the checkout session from Stripe with detailed error handling
    logger.info(f"Retrieving checkout session: {session_id}")
    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        logger.info(f"Successfully retrieved checkout session: {session_id}")
    except stripe.error.AuthenticationError as e:
        logger.error(f"Authentication with Stripe failed: {e}")
        internal_error(f"Authentication with Stripe failed")
    except stripe.error.InvalidRequestError as e:
        logger.error(f"Invalid session ID: {e}")
        bad_request(f"Invalid session ID")
    except Exception as e:
        logger.error(f"Error retrieving checkout session: {e}")
        internal_error(f"Error retrieving checkout session")
    
    # Verify the session was paid
    logger.info(f"Payment status: {checkout_session.payment_status}")
    if checkout_session.payment_status != "paid":
        logger.error(f"Payment not completed. Status: {checkout_session.payment_status}")
        bad_request(f"Payment not completed. Status: {checkout_session.payment_status}")
    
    # Get verification token - first try from query param, then from metadata
    verification_token = token
    metadata = getattr(checkout_session, 'metadata', {})
    
    # If token not provided in query, try to get from metadata
    if not verification_token and metadata:
        verification_token = metadata.get("verification_token")
    
    plan_id = metadata.get("plan_id") if metadata else None
    
    # Log detailed information for debugging
    logger.info(f"Metadata: token={verification_token}, plan={plan_id}")
    if not verification_token:
        logger.error(f"Missing verification token. Token in URL: {token}, Metadata: {metadata}")
        bad_request(f"Missing required verification token")
    
    if not plan_id:
        logger.error(f"Missing plan ID in session metadata. Metadata: {metadata}")
        bad_request(f"Missing required plan ID")
    
    # Get the pending account
    pending_account = db.query(PendingAccount).filter(
        PendingAccount.verification_token == verification_token
    ).first()
    
    if not pending_account:
        logger.error("Invalid registration. No matching pending account found.")
        not_found("Account", "registration")
    
    # Check if the pending account has expired
    if pending_account.expiration_date < datetime.now(timezone.utc):
        logger.error("Expired registration attempt")
        bad_request("Registration has expired. Please register again.")
    
    # Set a default subscription end date
    using_fallback = False
    subscription_id = None
    customer_id = None
    
    try:
        # Get plan duration from the subscription plan
        plan_duration_days = 30  # Default to monthly
        if plan_id in SUBSCRIPTION_PLANS and "duration_days" in SUBSCRIPTION_PLANS[plan_id]:
            plan_duration_days = SUBSCRIPTION_PLANS[plan_id]["duration_days"]
        
        # Default end date as fallback
        subscription_end_date = datetime.now(timezone.utc) + timedelta(days=plan_duration_days)
        subscription_status = "active"  # Default status
        
        # Try to get subscription details from Stripe
        if checkout_session.subscription:
            try:
                subscription = stripe.Subscription.retrieve(checkout_session.subscription)
                
                # Get the subscription status from Stripe
                if hasattr(subscription, 'status'):
                    subscription_status = subscription.status
                
                # Get the subscription end date
                if hasattr(subscription, 'current_period_end'):
                    end_timestamp = subscription.current_period_end
                    subscription_end_date = datetime.fromtimestamp(end_timestamp, tz=timezone.utc)
                    using_fallback = False
                elif isinstance(subscription, dict) and 'current_period_end' in subscription:
                    end_timestamp = subscription['current_period_end']
                    subscription_end_date = datetime.fromtimestamp(end_timestamp, tz=timezone.utc)
                    using_fallback = False
                else:
                    logger.warning("Could not find subscription end date in Stripe response, using fallback")
                    using_fallback = True
                    
                subscription_id = subscription.id
                
                # Get customer ID if available
                if hasattr(checkout_session, 'customer'):
                    customer_id = checkout_session.customer
                elif isinstance(checkout_session, dict) and 'customer' in checkout_session:
                    customer_id = checkout_session['customer']
            except Exception as e:
                logger.error(f"Error retrieving subscription details: {e}")
                logger.warning("Using fallback subscription details")
                using_fallback = True
                subscription_id = f"manual_{session_id}"
        else:
            logger.warning("No subscription ID found in checkout session, using fallback")
            subscription_id = f"manual_{session_id}"
            using_fallback = True
        
        # Create active user from pending account
        new_user = User(
            username=pending_account.username,
            hashed_password=pending_account.hashed_password,
            email=pending_account.email,
            company_name=pending_account.company_name,
            is_active=True,
            subscription_id=subscription_id,
            subscription_plan=plan_id,
            subscription_end_date=subscription_end_date,
            subscription_status=subscription_status,
            payment_method_id=customer_id
        )
        
        # Add the user to the database and remove the pending account
        db.add(new_user)
        db.delete(pending_account)
        db.commit()
        db.refresh(new_user)
        
        return new_user
        
    except stripe.error.StripeError as e:
        db.rollback()
        logger.error(f"Stripe error: {e}")
        internal_error(f"Error processing payment details")
    except Exception as e:
        db.rollback()
        logger.error(f"General error: {e}")
        internal_error(f"Error completing registration")

@checkout_router.post("/registration/{plan_id}", response_model=CheckoutSession)
async def create_registration_checkout(
    plan_id: str,
    token: str = Query(..., description="Verification token from registration"),
    db: Session = db_dependency
):
    """
    Create a checkout session for a new subscription during registration.
    
    This endpoint is used during the activation process of a pending account.
    The token parameter should contain the verification token from registration.
    
    Parameters:
    - plan_id: The plan to subscribe to (path parameter)
    - token: The verification token from the registration step (query parameter)
    
    Returns:
    - Checkout URL and session ID for Stripe checkout
    """
    # Verify the token corresponds to a pending account
    pending_account = db.query(PendingAccount).filter(
        PendingAccount.verification_token == token,
        PendingAccount.expiration_date > datetime.now(timezone.utc)
    ).first()
    
    if not pending_account:
        not_found("Registration", "token")
    
    # Get the price ID for the selected plan
    if plan_id not in SUBSCRIPTION_PLANS:
        not_found("Plan", plan_id)
    
    price_id = SUBSCRIPTION_PLANS[plan_id]["price_id"]
    
    # Create a checkout session
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=f"{settings.FRONTEND_URL}/registration/success?session_id={{CHECKOUT_SESSION_ID}}&token={token}",
            cancel_url=f"{settings.FRONTEND_URL}/registration/cancel",
            client_reference_id=pending_account.id,  # Store reference to pending account
            customer_email=pending_account.email,
            metadata={
                "verification_token": token,
                "plan_id": plan_id
            }
        )
        
        return CheckoutSession(
            checkout_url=checkout_session.url,
            session_id=checkout_session.id
        )
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        internal_error(f"Error creating checkout session: {str(e)}")