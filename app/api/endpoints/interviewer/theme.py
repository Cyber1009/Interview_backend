"""
Endpoints for company theme management with S3/local logo support.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import db_dependency, active_user_dependency
from app.core.database.models import User, UserTheme as UserThemeModel
from app.schemas.theme_schemas import UserTheme
from app.services.storage.logo_service import logo_service

# Create router
theme_router = APIRouter()

# SECTION: Theme Management

@theme_router.get("/", response_model=UserTheme)
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
    
    # Return theme with proper logo URL
    theme_data = UserTheme.from_orm(theme)
    # Use the logo service to get the appropriate logo URL
    logo_url = logo_service.get_logo_url(theme)
    if logo_url:
        theme_data.company_logo_url = logo_url
    
    return theme_data

@theme_router.put("/", response_model=UserTheme)
async def update_user_theme(
    theme_data: UserTheme,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """
    Update the current interviewer's theme settings with S3/local logo support.
    If no theme exists, a new one is created.
    """
    # Check if user already has a theme
    theme = db.query(UserThemeModel).filter(UserThemeModel.user_id == current_user.id).first()
    
    if not theme:
        # Create new theme
        theme = UserThemeModel(user_id=current_user.id)
        db.add(theme)
    
    # Handle logo upload if provided as data URL
    if theme_data.company_logo and theme_data.company_logo.startswith('data:'):
        try:
            # Delete old logo if it exists
            if theme.company_logo_url or theme.company_logo_s3_key:
                await logo_service.delete_logo(theme, db)
            
            # Upload new logo
            logo_result = await logo_service.upload_logo_from_data_url(
                theme_data.company_logo, 
                current_user.id
            )
            
            # Update with new storage information
            theme.company_logo_url = logo_result["file_url"]
            theme.storage_type = logo_result["storage_type"]
            
            if logo_result["storage_type"] == "s3":
                theme.company_logo_s3_key = logo_result.get("s3_key")
            else:
                theme.company_logo_s3_key = None
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to upload logo: {str(e)}"
            )
    
    # Update color properties
    theme.primary_color = theme_data.primary_color
    theme.accent_color = theme_data.accent_color
    theme.background_color = theme_data.background_color
    theme.text_color = theme_data.text_color
    
    db.commit()
    db.refresh(theme)
    
    # Return theme with proper logo URL
    theme_response = UserTheme.from_orm(theme)
    logo_url = logo_service.get_logo_url(theme)
    if logo_url:
        theme_response.company_logo_url = logo_url
    
    return theme_response


@theme_router.delete("/logo")
async def delete_logo(
    current_user: User = active_user_dependency,
    db: Session = db_dependency
):
    """Delete user's company logo from storage and database."""
    
    user_theme = db.query(UserThemeModel).filter(UserThemeModel.user_id == current_user.id).first()
    if not user_theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User theme not found"
        )
    
    success = await logo_service.delete_logo(user_theme, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete logo"
        )
    
    return {"message": "Logo deleted successfully"}
    
    return theme