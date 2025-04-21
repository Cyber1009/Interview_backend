"""
Webhook endpoint for receiving Stripe payment events.
"""
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import stripe
import os
import logging
from datetime import datetime, timedelta, timezone
import json
import hashlib
import hmac
from typing import Union, Dict, Any

from app.api.deps import db_dependency
from app.schemas.payment_schemas import WebhookEvent
from app.core.config import settings
from app.core.database.models import User
from app.utils.error_utils import bad_request, internal_error

# Create router
webhook_router = APIRouter()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@webhook_router.post("/", status_code=status.HTTP_200_OK, include_in_schema=False)
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

def get_value_safely(obj: Union[Dict[str, Any], object], attribute: str) -> Any:
    """
    Safely extract an attribute from either a dict or an object
    
    This helper function handles the different ways Stripe returns data (sometimes
    as a dict, sometimes as an object with attributes)
    """
    if isinstance(obj, dict):
        return obj.get(attribute)
    else:
        return getattr(obj, attribute, None)

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
    
    Marks the user's subscription as past_due if payment fails.
    """
    try:
        # Get customer ID from invoice
        customer_id = get_value_safely(invoice, "customer")
        subscription_id = get_value_safely(invoice, "subscription")
        
        if not customer_id:
            logger.error("Missing customer_id in payment failure event")
            return
            
        if not subscription_id:
            logger.info(f"No subscription ID in invoice {get_value_safely(invoice, 'id')}")
            return
        
        # Find user with this payment_method_id
        user = db.query(User).filter(User.payment_method_id == customer_id).first()
        if not user:
            logger.warning(f"No user found for customer_id: {customer_id}")
            return
        
        # Update subscription status to past_due
        user.subscription_status = "past_due"
        db.commit()
        logger.info(f"Marked subscription as past_due for user {user.id} due to payment failure")
    
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
        
        # Check if a user already exists with this token (already processed)
        from app.core.database.models import PendingAccount
        pending_account = db.query(PendingAccount).filter(
            PendingAccount.verification_token == verification_token
        ).first()
        
        if not pending_account:
            logger.info(f"No pending account found for token {verification_token} - possibly already processed")
            return
            
        logger.info(f"Processing registration checkout completion for token {verification_token}")
            
        # Process registration completion
        from app.core.database.models import User
        
        # Set subscription details
        subscription_id = get_value_safely(checkout_session, "subscription")
        customer_id = get_value_safely(checkout_session, "customer")
        
        # Default subscription duration
        from app.api.endpoints.payments.checkout import SUBSCRIPTION_PLANS
        plan_duration_days = 30  # Default to monthly
        if plan_id in SUBSCRIPTION_PLANS and "duration_days" in SUBSCRIPTION_PLANS[plan_id]:
            plan_duration_days = SUBSCRIPTION_PLANS[plan_id]["duration_days"]
            
        subscription_end_date = datetime.now(timezone.utc) + timedelta(days=plan_duration_days)
            
        # Try to get subscription details from Stripe if available
        subscription_status = "active"
        if subscription_id:
            try:
                subscription = stripe.Subscription.retrieve(subscription_id)
                if hasattr(subscription, 'status'):
                    subscription_status = subscription.status
                if hasattr(subscription, 'current_period_end'):
                    end_timestamp = subscription.current_period_end
                    subscription_end_date = datetime.fromtimestamp(end_timestamp, tz=timezone.utc)
            except Exception as e:
                logger.warning(f"Could not retrieve subscription details: {e}")
        
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
        
        logger.info(f"Successfully completed registration for {new_user.username} from webhook")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error handling checkout completion: {str(e)}")
        # Don't re-raise so webhook still returns 200