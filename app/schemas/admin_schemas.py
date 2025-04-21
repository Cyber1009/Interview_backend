"""
Administration related schemas.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AdminUserCreate(BaseModel):
    username: str
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "interviewer1",
                "password": "securePassword123"
            }
        }

class AdminActivateAccount(BaseModel):
    """Schema for admin to activate a pending account"""
    subscription_plan: Optional[str] = "basic"
    subscription_end_date: datetime 
    is_active: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "subscription_plan": "basic",
                "subscription_end_date": "2025-12-31T23:59:59",
                "is_active": True
            }
        }