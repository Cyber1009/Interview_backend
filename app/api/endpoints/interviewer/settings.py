"""
Endpoints for interviewer settings management.
Handles various user preferences including theme settings and notification preferences.
"""
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.api.dependencies import db_dependency, active_user_dependency
from app.core.database.models import User, UserTheme as UserThemeModel
from app.schemas.theme_schemas import UserTheme
from app.services.storage.storage_factory import get_storage

# Create router
router = APIRouter()

# ======================================================================
# SECTION: Theme Settings
# ======================================================================

@router.get("/theme", response_model=UserTheme)
def get_user_theme(
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """
    Get the current interviewer's theme settings.
    If no theme exists, a default theme is created.
    """
    # Check if user already has a theme
    theme = db.query(UserThemeModel).filter(UserThemeModel.user_id == current_user.id).first()
    
    # If no theme exists, create a default one
    if not theme:
        theme = UserThemeModel(user_id=current_user.id)
        db.add(theme)
        db.commit()
        db.refresh(theme)
    
    return theme

@router.put("/theme", response_model=UserTheme)
def update_user_theme(
    theme_data: UserTheme,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """
    Update the current interviewer's theme settings.
    If no theme exists, a new one is created.
    """
    # Check if user already has a theme
    theme = db.query(UserThemeModel).filter(UserThemeModel.user_id == current_user.id).first()
    
    if not theme:
        # Create new theme with provided data
        theme = UserThemeModel(user_id=current_user.id, **theme_data.dict())
        db.add(theme)
    else:
        # Update existing theme using our schema's utility method
        for attr, value in theme_data.dict().items():
            setattr(theme, attr, value)
    
    db.commit()
    db.refresh(theme)
    
    return theme

# ======================================================================
# SECTION: Additional Settings (Extensible for future growth)
# ======================================================================

# Example of future extension point - not implemented yet
# @router.get("/notifications", response_model=UserNotificationSettings)
# def get_notification_settings(
#    db: Session = db_dependency,
#    current_user: User = active_user_dependency
# ):
#    """Get the current interviewer's notification preferences"""
#    pass

# This router alias is kept for backward compatibility but should not be used directly.
# All theme endpoints should be accessed via the /settings prefix (e.g., /interviewer/settings/theme)
theme_router = router