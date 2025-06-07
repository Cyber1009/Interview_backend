"""
Endpoints for interviewer profile management.
"""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import db_dependency, active_user_dependency
from app.core.database.models import User
from app.schemas.auth_schemas import UserProfile
from app.utils.subscription_utils import update_subscription_status

# Create router
router = APIRouter()

@router.get("", 
                  response_model=UserProfile,
                  summary="Interviewer Profile",
                  description="Get profile information for the currently authenticated interviewer")
def get_profile(
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """
    Get current interviewer's profile information.
    
    This endpoint returns the profile information for the currently authenticated interviewer,
    including their subscription status, account details, and preferences.
    
    It automatically updates the subscription status based on the current date
    and subscription end date before returning the user profile.
    
    Returns:
    - Complete user profile with up-to-date subscription status
    """
    # Re-fetch the user from the database to get the most up-to-date information
    fresh_user_data = db.query(User).filter(User.id == current_user.id).first()
    
    # If for some reason we can't find the user (very unlikely), fall back to current_user
    if not fresh_user_data:
        return current_user
    
    # Update subscription status if needed
    update_subscription_status(fresh_user_data, db)
    
    return fresh_user_data