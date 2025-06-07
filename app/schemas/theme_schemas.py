"""
UI theme customization related schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

# Default theme color constants that can be imported by other modules
# Updated based on sample.html design
DEFAULT_PRIMARY_COLOR = "#091326"    # Dark blue from button-bg
DEFAULT_ACCENT_COLOR = "#52606d"     # Muted blue from label-color
DEFAULT_BACKGROUND_COLOR = "#f5f7fa" # Light gray from search-bg
DEFAULT_TEXT_COLOR = "#222222"       # Dark text color from body

class UserTheme(BaseModel):
    """Schema for user interface theme customization"""
    # Brand elements - Support both new and legacy logo storage
    company_logo: Optional[str] = Field(default=None, description="Legacy: Data URL for logo image")
    company_logo_url: Optional[str] = Field(default=None, description="Current logo URL (S3 or local)")
    storage_type: Optional[str] = Field(default="local", description="Storage type: 'local' or 's3'")
    
    # Simplified color palette (4 essential colors)
    primary_color: str = Field(default=DEFAULT_PRIMARY_COLOR, description="Primary brand color for buttons and key UI elements")
    accent_color: str = Field(default=DEFAULT_ACCENT_COLOR, description="Accent color for highlights and important actions")
    background_color: str = Field(default=DEFAULT_BACKGROUND_COLOR, description="Main background color for pages")
    text_color: str = Field(default=DEFAULT_TEXT_COLOR, description="Default text color that works on the background")
    
    class Config:
        from_attributes = True
        
    @classmethod
    def create_update_dict(cls, **kwargs) -> Dict[str, Any]:
        """
        Create a dictionary with only the provided fields for partial updates.
        
        Usage:
            update_data = UserTheme.create_update_dict(primary_color="#ff0000", text_color="#ffffff")
        """
        update_dict = {}
        
        # Version-compatible approach
        try:
            # Pydantic v2 approach
            valid_fields = cls.model_fields.keys()
        except AttributeError:
            # Fallback for Pydantic v1
            valid_fields = cls.__fields__.keys()
        
        for key, value in kwargs.items():
            if key in valid_fields and value is not None:
                update_dict[key] = value
                
        return update_dict