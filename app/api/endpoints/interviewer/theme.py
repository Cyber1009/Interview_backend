"""
Endpoints for company theme management.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_dependency, active_user_dependency
from app.core.database.models import User, UserTheme
from app.schemas import UserThemeUpdate, UserThemeResponse

# Create router
theme_router = APIRouter()

@theme_router.get("/theme", response_model=UserThemeResponse)
def get_user_theme(
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """
    Get the current interviewer's theme settings.
    If no theme exists, a default theme is created.
    """
    # Check if user already has a theme
    theme = db.query(UserTheme).filter(UserTheme.user_id == current_user.id).first()
    
    # If no theme exists, create a default one
    if not theme:
        theme = UserTheme(user_id=current_user.id)
        db.add(theme)
        db.commit()
        db.refresh(theme)
    
    return theme

@theme_router.put("/theme", response_model=UserThemeResponse)
def update_user_theme(
    theme_data: UserThemeUpdate,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """
    Update the current interviewer's theme settings.
    If no theme exists, a new one is created.
    """
    # Check if user already has a theme
    theme = db.query(UserTheme).filter(UserTheme.user_id == current_user.id).first()
    
    if not theme:
        # Create new theme with provided data
        theme = UserTheme(
            user_id=current_user.id,
            company_logo=theme_data.company_logo,
            primary_color=theme_data.primary_color,
            secondary_color=theme_data.secondary_color,
            accent_color=theme_data.accent_color,
            background_color=theme_data.background_color
        )
        db.add(theme)
    else:
        # Update existing theme
        theme.company_logo = theme_data.company_logo
        theme.primary_color = theme_data.primary_color
        theme.secondary_color = theme_data.secondary_color
        theme.accent_color = theme_data.accent_color
        theme.background_color = theme_data.background_color
    
    db.commit()
    db.refresh(theme)
    
    return theme