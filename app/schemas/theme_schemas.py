"""
UI theme customization related schemas.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Theme Schemas
class UserThemeBase(BaseModel):
    company_logo: Optional[str] = None
    primary_color: str = "#3498db"
    secondary_color: str = "#2ecc71"
    accent_color: str = "#e74c3c"
    background_color: str = "#f5f5f5"

class UserThemeCreate(UserThemeBase):
    pass

class UserThemeUpdate(UserThemeBase):
    pass

class UserThemeResponse(UserThemeBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True