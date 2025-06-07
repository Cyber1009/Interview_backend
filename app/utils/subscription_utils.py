"""
Utilities for managing subscription statuses.
"""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
import stripe
from typing import Optional, Dict, Any, Tuple, Union

# Fix import path for User model
from app.core.database.models import User, PendingAccount
from app.utils.datetime_utils import get_utc_now, safe_compare_dates

logger = logging.getLogger(__name__)

def update_subscription_status(user: User, db: Session) -> None:
    """
    Update a user's subscription status based on their subscription end date.
    
    Args:
        user: The user object to update
        db: Database session for committing changes
    
    Returns:
        None, but updates the user object and commits changes to the database
    """
    now = get_utc_now()
    
    # If there's no subscription end date, we assume inactive
    if not user.subscription_end_date:
        if user.is_active or user.subscription_status != "inactive":
            logger.info(f"User {user.id} has no subscription end date, marking as inactive")
            user.is_active = False
            user.subscription_status = "inactive"
            db.commit()
        return
        
    # Check if subscription has expired
    if now > user.subscription_end_date:
        if user.is_active or user.subscription_status != "expired":
            logger.info(f"User {user.id} subscription expired, updating status")
            user.is_active = False
            user.subscription_status = "expired"
            db.commit()
    else:
        # Subscription is current
        if not user.is_active or user.subscription_status != "active":
            logger.info(f"User {user.id} subscription active, updating status")
            user.is_active = True
            user.subscription_status = "active"
            db.commit()

def sync_all_subscription_statuses(db: Session) -> int:
    """
    Update subscription statuses for all users in the database.
    
    Args:
        db: Database session
        
    Returns:
        Number of records updated
    """
    now = get_utc_now()
    updates = 0
    
    # Find users with expired subscriptions who are still marked active
    expired_users = db.query(User).filter(
        User.subscription_end_date < now,
        User.is_active == True
    ).all()
    
    for user in expired_users:
        user.is_active = False
        user.subscription_status = "expired"
        updates += 1
    
    # Find users with current subscriptions who are marked inactive
    active_users = db.query(User).filter(
        User.subscription_end_date > now,
        User.is_active == False
    ).all()
    
    for user in active_users:
        user.is_active = True
        user.subscription_status = "active"
        updates += 1
        
    if updates > 0:
        db.commit()
        logger.info(f"Updated subscription status for {updates} users")
        
    return updates

def process_registration_completion(
    db: Session, 
    verification_token: str, 
    subscription_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    plan_id: Optional[str] = None,
    subscription_status: str = "active",
    subscription_end_date: Optional[datetime] = None
) -> Tuple[User, bool]:
    """
    Complete a user registration by converting a pending account to an active user.
    
    This function is used by both the webhook handler and the registration completion endpoint
    to avoid code duplication.
    
    Args:
        db: Database session
        verification_token: The verification token for the pending account
        subscription_id: Stripe subscription ID (optional)
        customer_id: Stripe customer ID (optional)
        plan_id: Subscription plan ID (optional)
        subscription_status: Subscription status (defaults to "active")
        subscription_end_date: Subscription end date (optional)
        
    Returns:
        Tuple of (User object, Success boolean)
    """
    try:
        # Find the pending account
        pending_account = db.query(PendingAccount).filter(
            PendingAccount.verification_token == verification_token
        ).first()
        
        if not pending_account:
            logger.warning(f"No pending account found for token {verification_token}")
            return None, False
        
        # Check if the pending account has expired
        if pending_account.expiration_date < datetime.now(timezone.utc):
            logger.error("Expired registration attempt")
            return None, False
            
        # Create active user from pending account
        new_user = User(
            username=pending_account.username,
            hashed_password=pending_account.hashed_password,
            email=pending_account.email,
            company=pending_account.company,
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
        
        logger.info(f"Successfully completed registration for {new_user.username}")
        return new_user, True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error completing registration: {str(e)}")
        return None, False

def get_subscription_end_date(
    subscription_id: str, 
    plan_id: str, 
    fallback_days: int = 30
) -> Tuple[datetime, bool]:
    """
    Get the subscription end date from Stripe, or calculate a fallback date.
    
    Args:
        subscription_id: Stripe subscription ID
        plan_id: Plan ID for fallback calculation
        fallback_days: Number of days to use for fallback
        
    Returns:
        Tuple of (end_date, using_fallback)
    """
    using_fallback = False
    
    # Use the centralized subscription plans configuration
    from app.core.config import SubscriptionPlansConfig
    try:
        # Try to get duration_days from the plan configuration
        fallback_days = SubscriptionPlansConfig.get_duration_days(plan_id)
    except Exception as e:
        # If plan doesn't exist or doesn't have duration_days, use default
        logger.warning(f"Could not get duration for plan {plan_id}: {e}")
        pass
        
    # Default end date as fallback
    end_date = datetime.now(timezone.utc) + timedelta(days=fallback_days)
    
    # Try to get subscription details from Stripe if available
    if subscription_id:
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            if hasattr(subscription, 'current_period_end'):
                end_timestamp = subscription.current_period_end
                end_date = datetime.fromtimestamp(end_timestamp, tz=timezone.utc)
                using_fallback = False
            elif isinstance(subscription, dict) and 'current_period_end' in subscription:
                end_timestamp = subscription['current_period_end']
                end_date = datetime.fromtimestamp(end_timestamp, tz=timezone.utc)
                using_fallback = False
            else:
                using_fallback = True
        except Exception as e:
            logger.warning(f"Could not retrieve subscription details: {e}")
            using_fallback = True
    else:
        using_fallback = True
        
    return end_date, using_fallback
