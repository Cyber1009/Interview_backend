"""
Consolidated endpoints for payment processing and subscription management.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging
from typing import Dict, Optional, List, Any, Union
import stripe
from datetime import datetime, timedelta, timezone

from app.core.database.models import User, PendingAccount
from app.schemas.payment_schemas import (
    CheckoutSession, CustomerPortalSession, SubscriptionPlanList, 
    SubscriptionPlanFeatures
)
from app.schemas.auth_schemas import UserResponse, RegistrationResponse
from app.core.config import settings, SubscriptionPlansConfig, SUBSCRIPTION_PLANS
from app.api.exceptions import not_found, bad_request, internal_error
from app.api.dependencies import db_dependency, active_user_dependency
from app.utils.subscription_utils import process_registration_completion, get_subscription_end_date

# Configure logger
logger = logging.getLogger(__name__)

# Configure Stripe API key
stripe.api_key = settings.STRIPE_API_KEY

# Configure subscription plans
SUBSCRIPTION_PLANS = {
    "basic": {
        "name": "Basic Plan",
        "price_id": settings.STRIPE_BASIC_PRICE_ID,
        "description": "Basic access to interview platform",
        "features": ["5 interviews per month", "Basic analytics", "24-hour support"],
        "price_display": "$9.99/month"
    },
    "premium": {
        "name": "Premium Plan",
        "price_id": settings.STRIPE_PREMIUM_PRICE_ID,
        "description": "Premium access to interview platform",
        "features": ["20 interviews per month", "Advanced analytics", "Priority support", "Custom branding"],
        "price_display": "$29.99/month"
    },
    "enterprise": {
        "name": "Enterprise Plan",
        "price_id": settings.STRIPE_ENTERPRISE_PRICE_ID,
        "description": "Enterprise-level access to interview platform",
        "features": ["Unlimited interviews", "Full analytics suite", "Dedicated support", "Custom branding", "API access"],
        "price_display": "$99.99/month"
    }
}

# Helper function for webhook processing
def get_value_safely(obj: Any, key: str) -> Any:
    """Safely get a value from a dictionary or object, handling potential None values"""
    if obj is None:
        return None
        
    if isinstance(obj, dict):
        return obj.get(key)
    else:
        return getattr(obj, key, None)

async def fetch_plans_from_stripe() -> Dict[str, Any]:
    """Fetch subscription plan details from Stripe or return defaults"""
    try:
        # For now, just return the static plans
        # In future, could implement dynamic plan fetching from Stripe Products API
        return SubscriptionPlansConfig.get_plans()
    except Exception as e:
        logger.error(f"Error fetching plans from Stripe: {str(e)}")
        return SUBSCRIPTION_PLANS
    
# Create main payment router
payment_router = APIRouter()

# Plans endpoint
@payment_router.get("/plans", response_model=SubscriptionPlanList)
async def get_subscription_plans():
    """
    Get available subscription plans.
    
    Returns information about all available subscription plans:
    - Basic
    - Premium
    - Enterprise
    """
    try:
        # Get plans (potentially from Stripe)
        stripe_plans = await fetch_plans_from_stripe()
        
        # Map Stripe plans to our SubscriptionPlanList format
        return SubscriptionPlanList(
            basic=SubscriptionPlanFeatures(**stripe_plans.get("basic", SUBSCRIPTION_PLANS["basic"])),
            premium=SubscriptionPlanFeatures(**stripe_plans.get("premium", SUBSCRIPTION_PLANS["premium"])),
            enterprise=SubscriptionPlanFeatures(**stripe_plans.get("enterprise", SUBSCRIPTION_PLANS["enterprise"]))
        )
    except Exception as e:
        logger.error(f"Error getting subscription plans: {str(e)}")
        internal_error("Error fetching subscription plans")

# Checkout endpoint - unified for new registrations and existing users
@payment_router.post("/checkout/{plan_id}", response_model=CheckoutSession)
async def create_checkout_session(
    plan_id: str,
    token: Optional[str] = Query(None, description="Verification token for new registrations"),
    db: Session = db_dependency,
    current_user: Optional[User] = Depends(lambda: None)  # Make current_user optional
):
    """
    Unified endpoint for creating checkout sessions for both new registrations and existing users.
    
    This endpoint automatically detects whether it's being used for:
    1. New user registration (when token is provided)
    2. Existing user subscription management (when authenticated user is present)
    
    Parameters:
    - plan_id: The plan to subscribe to (path parameter)
    - token: Optional verification token from registration (query parameter)
    
    Returns:
    - Checkout URL and session ID for Stripe checkout
    """
    # Determine if this is for a new registration or existing user
    if token:
        # This is a new registration checkout
        pending_account = db.query(PendingAccount).filter(
            PendingAccount.verification_token == token,
            PendingAccount.expiration_date > datetime.now(timezone.utc)
        ).first()
        
        if not pending_account:
            not_found("Registration", "token")
            
        client_id = pending_account.id
        client_email = pending_account.email
        success_url = f"{settings.FRONTEND_URL}/registration/success?session_id={{CHECKOUT_SESSION_ID}}&token={token}"
        cancel_url = f"{settings.FRONTEND_URL}/registration/cancel"
        metadata = {
            "verification_token": token,
            "plan_id": plan_id,
            "action": "new_registration"
        }
        
    elif current_user:
        # This is for an existing user
        client_id = current_user.id
        client_email = current_user.email
        success_url = f"{settings.FRONTEND_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{settings.FRONTEND_URL}/subscription/cancel"
        metadata = {
            "user_id": current_user.id,
            "plan_id": plan_id,
            "action": "reactivate" if not current_user.is_active else "change_plan" 
        }
        
    else:
        # Neither token nor logged in user provided
        bad_request("Either verification token or authentication required")

    # Get the price ID for the selected plan
    if plan_id not in SUBSCRIPTION_PLANS:
        not_found("Plan", plan_id)
    # Get the price ID for the selected plan
    try:
        price_id = SubscriptionPlansConfig.get_price_id(plan_id)
    except KeyError:
        not_found("Plan", plan_id)
        price_id = SUBSCRIPTION_PLANS[plan_id]["price_id"]
    
    # Create checkout session
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
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=client_id,
            customer_email=client_email,
            metadata=metadata
        )
        
        return CheckoutSession(
            checkout_url=checkout_session.url,
            session_id=checkout_session.id
        )
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        internal_error(f"Error creating checkout session: {str(e)}")

# Complete checkout endpoint - unified for new registrations and existing users
@payment_router.post("/complete-checkout", response_model=UserResponse)
async def complete_checkout_process(
    session_id: str = Query(..., description="Stripe checkout session ID"),
    token: Optional[str] = Query(None, description="Verification token (for new registrations)"),
    db: Session = db_dependency,
    current_user: Optional[User] = Depends(lambda: None)  # Make current_user optional
):
    """
    Complete the checkout process after successful payment.
    
    This unified endpoint handles both:
    1. New registration completion
    2. Existing subscription management (reactivation/change)
    
    Parameters:
    - session_id: Stripe checkout session ID
    - token: Optional verification token for new registrations
    
    Returns:
    - User details with updated subscription information
    """
    # Retrieve the checkout session from Stripe
    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
    except Exception as e:
        logger.error(f"Error retrieving checkout session: {e}")
        internal_error(f"Error retrieving checkout session")
    
    # Verify the session was paid
    if checkout_session.payment_status != "paid":
        bad_request(f"Payment not completed. Status: {checkout_session.payment_status}")
    
    # Get metadata from the session
    metadata = getattr(checkout_session, 'metadata', {})
    action = metadata.get("action", "")
    plan_id = metadata.get("plan_id")
    
    # Extract subscription info from the session
    subscription_id = checkout_session.subscription if hasattr(checkout_session, 'subscription') else None
    customer_id = checkout_session.customer if hasattr(checkout_session, 'customer') else None
    
    # Get subscription end date using utility function
    subscription_end_date, using_fallback = get_subscription_end_date(subscription_id, plan_id)
    subscription_status = "active"
    
    if action == "new_registration" or (not current_user and token):
        # Handle new registration completion
        verification_token = token or metadata.get("verification_token")
        if not verification_token:
            bad_request("Missing verification token for registration")
            
        user, success = process_registration_completion(
            db,
            verification_token,
            subscription_id,
            customer_id,
            plan_id,
            subscription_status,
            subscription_end_date
        )
        
        if not success or not user:
            internal_error("Error completing registration")
            
        return user
        
    elif current_user or metadata.get("user_id"):
        # Handle existing user subscription update
        user_id = current_user.id if current_user else metadata.get("user_id")
        if not user_id:
            bad_request("User identification missing")
            
        # Get the user record
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            not_found("User", user_id)
            
        # Update subscription information
        user.is_active = True
        user.subscription_status = subscription_status
        user.subscription_id = subscription_id
        user.payment_method_id = customer_id
        user.subscription_plan = plan_id
        user.subscription_end_date = subscription_end_date
        
        db.commit()
        db.refresh(user)
        
        return user
    
    else:        bad_request("Unable to identify checkout action type")

# Customer portal endpoint
@payment_router.post("/customer-portal", response_model=CustomerPortalSession)
async def create_customer_portal_session(
    current_user: User = active_user_dependency,
    db: Session = db_dependency
):
    """
    Create a Stripe Customer Portal session for subscription management.
    
    This allows users to:
    - Update payment methods
    - Change subscription plans
    - Cancel subscriptions
    
    Returns a URL to the Stripe Customer Portal
    """
    if not current_user.payment_method_id:
        bad_request("No payment method associated with this account")
    
    try:
        # Create a new customer portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.payment_method_id,
            return_url=f"{settings.FRONTEND_URL}/account"
        )
        
        return CustomerPortalSession(url=portal_session.url)
    except Exception as e:
        logger.error(f"Error creating customer portal: {str(e)}")
        internal_error(f"Error creating customer portal session")

# Webhook endpoint
@payment_router.post("/webhook", status_code=status.HTTP_200_OK, include_in_schema=False)
async def handle_stripe_webhook(request: Request, db: Session = db_dependency):
    """
    Process Stripe webhook events.
    
    This endpoint receives events from Stripe about subscription changes,
    payment successes/failures, and other events that require synchronization
    with our database.
    
    Events handled:
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_succeeded
    - invoice.payment_failed
    
    Returns:
    - Success message
    """
    try:
        # Read raw payload
        payload = await request.body()
        
        # Get signature from headers
        sig_header = request.headers.get("stripe-signature")
        if not sig_header:
            bad_request("Missing Stripe signature header")
        
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            # Invalid payload
            logger.error(f"Invalid Stripe payload: {e}")
            bad_request("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            logger.error(f"Invalid Stripe signature: {e}")
            bad_request("Invalid signature")
        
        # Extract event data
        event_data = event.data.object
        event_type = event.type
        
        logger.info(f"Received Stripe webhook: {event_type}")
        
        # Handle different event types
        if event_type == "customer.subscription.created" or event_type == "customer.subscription.updated":
            await handle_subscription_update(db, event_data)
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_cancellation(db, event_data)
        elif event_type == "invoice.payment_succeeded":
            await handle_payment_success(db, event_data)
        elif event_type == "invoice.payment_failed":
            await handle_payment_failure(db, event_data)
        elif event_type == "checkout.session.completed":
            # For handling immediate checkout completion
            await handle_checkout_completion(db, event_data)
        
        return {"status": "success", "message": f"Processed {event_type}"}
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        internal_error(f"Error processing webhook: {str(e)}")

# Webhook handlers
async def handle_subscription_update(db: Session, subscription):
    """
    Handle subscription creation or update event.
    
    Updates the user's subscription details in our database.
    """
    try:
        # Get customer ID from subscription
        customer_id = get_value_safely(subscription, "customer")
        subscription_id = get_value_safely(subscription, "id")
        
        if not customer_id:
            logger.error(f"Missing customer_id in subscription update for subscription {subscription_id}")
            return
        
        # Find user with this payment_method_id
        user = db.query(User).filter(User.payment_method_id == customer_id).first()
        if not user:
            logger.warning(f"No user found for customer_id: {customer_id}")
            return
        
        # Update subscription details
        user.subscription_id = subscription_id
        
        # Get subscription status
        status = get_value_safely(subscription, "status")
        if status:
            user.subscription_status = status
            user.is_active = status == "active"
        
        # Get subscription end date
        current_period_end = get_value_safely(subscription, "current_period_end")
        if current_period_end:
            user.subscription_end_date = datetime.fromtimestamp(current_period_end, tz=timezone.utc)
        
        # Get metadata if available to determine plan
        metadata = get_value_safely(subscription, "metadata")
        if metadata:
            plan_id = get_value_safely(metadata, "plan_id")
            if plan_id:
                user.subscription_plan = plan_id
        
        db.commit()
        logger.info(f"Updated subscription for user {user.id} - status: {user.subscription_status}")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating subscription: {str(e)}")
        raise e

async def handle_subscription_cancellation(db: Session, subscription):
    """
    Handle subscription cancellation event.
    
    Marks the user's subscription as canceled in our database.
    """
    try:
        # Get customer ID from subscription
        customer_id = get_value_safely(subscription, "customer")
        
        if not customer_id:
            logger.error("Missing customer_id in subscription cancellation event")
            return
            
        # Find user with this payment_method_id
        user = db.query(User).filter(User.payment_method_id == customer_id).first()
        if not user:
            logger.warning(f"No user found for customer_id: {customer_id}")
            return
        
        # Update subscription details
        user.subscription_status = "canceled"
        user.is_active = False
        
        db.commit()
        logger.info(f"Marked subscription as canceled for user {user.id}")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error handling subscription cancellation: {str(e)}")
        raise e

async def handle_payment_success(db: Session, invoice):
    """
    Handle successful payment event.
    
    Updates the user's subscription status to active if it was previously 
    in a non-active state due to payment issues.
    """
    try:
        # Get customer ID from invoice
        customer_id = get_value_safely(invoice, "customer")
        subscription_id = get_value_safely(invoice, "subscription")
        
        if not customer_id:
            logger.error("Missing customer_id in payment success event")
            return
            
        if not subscription_id:
            logger.info(f"No subscription ID in invoice {get_value_safely(invoice, 'id')}")
            return
        
        # Find user with this payment_method_id
        user = db.query(User).filter(User.payment_method_id == customer_id).first()
        if not user:
            logger.warning(f"No user found for customer_id: {customer_id}")
            return
        
        # Update subscription status if it's not already active
        if user.subscription_status != "active":
            user.subscription_status = "active"
            user.is_active = True
            
            db.commit()
            logger.info(f"Reactivated subscription for user {user.id} after payment success")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error handling payment success: {str(e)}")
        raise e

async def handle_payment_failure(db: Session, invoice):
    """
    Handle failed payment event.
    
    Marks the user's subscription as past_due when a payment fails.
    """
    try:
        # Get customer ID from invoice
        customer_id = get_value_safely(invoice, "customer")
        
        if not customer_id:
            logger.error("Missing customer_id in payment failure event")
            return
        
        # Find user with this payment_method_id
        user = db.query(User).filter(User.payment_method_id == customer_id).first()
        if not user:
            logger.warning(f"No user found for customer_id: {customer_id}")
            return
        
        # Update subscription status
        user.subscription_status = "past_due"
        # Don't deactivate user yet - they'll get dunning emails and a grace period
        
        db.commit()
        logger.info(f"Marked subscription as past_due for user {user.id}")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error handling payment failure: {str(e)}")
        raise e

async def handle_checkout_completion(db: Session, checkout_session):
    """
    Handle checkout session completion event.
    
    This is an important backup mechanism in case the client doesn't call
    the /registration/complete endpoint after successful payment.
    """
    try:
        # Only process completed checkouts
        payment_status = get_value_safely(checkout_session, "payment_status")
        if payment_status != "paid":
            logger.info(f"Checkout not paid yet. Status: {payment_status}")
            return
        
        # Check if this is a registration checkout
        metadata = get_value_safely(checkout_session, "metadata")
        if not metadata:
            logger.info("No metadata in checkout session")
            return
            
        verification_token = get_value_safely(metadata, "verification_token")
        if not verification_token:
            logger.info("Not a registration checkout (no verification_token)")
            return
            
        plan_id = get_value_safely(metadata, "plan_id")
        if not plan_id:
            logger.warning("Missing plan_id in registration checkout metadata")
            return
            
        logger.info(f"Processing registration checkout completion for token {verification_token}")
            
        # Set subscription details
        subscription_id = get_value_safely(checkout_session, "subscription")
        customer_id = get_value_safely(checkout_session, "customer")
        
        # Get subscription end date and status
        subscription_status = "active"
        if subscription_id:
            try:
                subscription = stripe.Subscription.retrieve(subscription_id)
                if hasattr(subscription, 'status'):
                    subscription_status = subscription.status
            except Exception as e:
                logger.warning(f"Could not retrieve subscription status: {e}")
                
        # Get subscription end date using utility function
        subscription_end_date, _ = get_subscription_end_date(subscription_id, plan_id)
        
        # Process registration completion using utility function
        user, success = process_registration_completion(
            db,
            verification_token,
            subscription_id,
            customer_id,
            plan_id,
            subscription_status,
            subscription_end_date
        )
        
        if success:
            logger.info(f"Successfully completed registration for {user.username} from webhook")
        else:
            logger.warning("Registration completion failed from webhook")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error handling checkout completion: {str(e)}")
        # Don't re-raise so webhook still returns 200

# ==========================================
# Registration-Specific Endpoints
# ==========================================

@payment_router.post("/registration/{plan_id}", response_model=CheckoutSession)
async def create_registration_checkout(
    plan_id: str,
    token: str = Query(..., description="Verification token from registration"),
    db: Session = db_dependency
):
    """
    Create a checkout session for a new subscription during registration.
    
    This endpoint is part of the account activation flow, allowing new users 
    to select a subscription plan and process payment.
    
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

@payment_router.post("/registration/complete", response_model=UserResponse)
async def complete_registration(
    session_id: str = Query(..., description="Stripe checkout session ID"),
    token: Optional[str] = Query(None, description="Verification token (optional if stored in session metadata)"),
    db: Session = db_dependency
):
    """
    Complete the signup process after successful payment.
    
    This endpoint finalizes the registration process by converting a pending account
    to an active user account after successful payment processing.
    
    Parameters:
    - **session_id**: Stripe checkout session ID (passed as query parameter)
    - **token**: Optional verification token (if not provided, will try to get it from session metadata)
    
    Returns:
    - Full user details for the newly created account
    """
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
    
    # Set subscription details
    subscription_id = checkout_session.subscription if hasattr(checkout_session, 'subscription') else None
    customer_id = checkout_session.customer if hasattr(checkout_session, 'customer') else None
    
    # Get subscription end date using utility function
    subscription_end_date, using_fallback = get_subscription_end_date(subscription_id, plan_id)
    subscription_status = "active"  # Default status
    
    # Try to get subscription status from Stripe if available
    if subscription_id:
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            if hasattr(subscription, 'status'):
                subscription_status = subscription.status
        except Exception as e:
            logger.warning(f"Could not retrieve subscription status: {e}")
    
    # Process registration completion using utility function
    try:
        user, success = process_registration_completion(
            db,
            verification_token,
            subscription_id,
            customer_id,
            plan_id,
            subscription_status,
            subscription_end_date
        )
        
        if not success or not user:
            logger.error("Registration completion failed")
            internal_error("Error completing registration")
            
        return user
        
    except stripe.error.StripeError as e:
        db.rollback()
        logger.error(f"Stripe error: {e}")
        internal_error(f"Error processing payment details")
    except Exception as e:
        db.rollback()
        logger.error(f"General error: {e}")
        internal_error(f"Error completing registration")

# ==========================================
# Subscription Reactivation
# ==========================================

@payment_router.post("/reactivate-subscription/{plan_id}", response_model=CheckoutSession)
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