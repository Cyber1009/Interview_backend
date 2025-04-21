"""
Shared API dependencies.
Provides consistent dependency injection across all API endpoints.
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.database.models import User
from app.core.security import get_current_user, check_subscription_status, oauth2_scheme

# Database session dependency
db_dependency = Depends(get_db)

# User dependencies
user_dependency = Depends(get_current_user)

# Middleware to check if user's subscription is active
def get_active_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify user has an active subscription.
    
    This middleware only checks if the subscription is active 
    using the status that was already updated in get_current_user.
    """
    # No need to call check_subscription_status again as it's already done in get_current_user
    # Just verify the current status
    if not current_user.is_active or current_user.subscription_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscription inactive or expired. Please renew your subscription."
        )
    
    return current_user

# Active user dependency 
active_user_dependency = Depends(get_active_user)

# Role-specific dependencies - making it clear which endpoints require which roles
interviewer_dependency = active_user_dependency  # Interviewers need active subscriptions
admin_dependency = user_dependency  # Admin auth is handled separately with HTTP Basic Auth