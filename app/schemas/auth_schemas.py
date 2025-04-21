"""
Authentication and user-related schemas.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, ForwardRef, List
from datetime import datetime

# Forward reference to avoid circular imports
UserThemeResponse = ForwardRef("UserThemeResponse")

# Registration Schemas
class RegistrationCreate(BaseModel):
    username: str
    password: str  # Removed default empty string to make password required
    email: EmailStr
    company_name: Optional[str] = None

class RegistrationResponse(BaseModel):
    username: str
    email: str
    verification_token: str
    expiration_date: datetime
    
    class Config:
        from_attributes = True

class AccountActivation(BaseModel):
    verification_token: str
    plan_id: str

# Add the missing schemas
class StripeCheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str

class RegistrationCheckout(BaseModel):
    verification_token: str

class RegistrationComplete(BaseModel):
    session_id: str
    verification_token: Optional[str] = None

# Auth Schemas
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    email: Optional[str] = None
    company_name: Optional[str] = None

class UserResponse(UserBase):
    id: int
    email: Optional[str] = None
    company_name: Optional[str] = None
    is_active: bool
    subscription_status: Optional[str] = None
    subscription_plan: Optional[str] = None
    subscription_end_date: Optional[datetime] = None
    created_at: datetime
    theme: Optional[UserThemeResponse] = None
    
    class Config:
        from_attributes = True  # Updated from orm_mode = True for Pydantic v2

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Password Management
class PasswordChange(BaseModel):
    current_password: str
    new_password: str

# Resolve forward references
from app.schemas.theme_schemas import UserThemeResponse
UserResponse.model_rebuild()