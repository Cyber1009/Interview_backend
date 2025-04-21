"""
Utilities for managing subscription statuses.
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

# Fix import path for User model
from app.core.database.models import User
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
