"""
Authentication and user-related schemas.
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Any
from datetime import datetime

from app.schemas.base_schemas import (
    UserBase, 
    UserCredentialsBase,
    SubscriptionBase,
    VerificationBase
)

# --- Authentication schemas ---

class AuthToken(BaseModel):
    """JWT token response schema"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for data stored in JWT token"""
    username: Optional[str] = None


class PasswordChange(BaseModel):
    """Schema for password change request"""
    current_password: str
    new_password: str


# --- Registration schemas ---

class RegistrationCreate(UserCredentialsBase):
    """Schema for new user registration request"""
    # Override email to make it required (non-optional) for registration
    email: EmailStr


class RegistrationResponse(UserBase, VerificationBase):
    """Schema for registration response with verification token"""
    expiration_date: datetime
    
    class Config:
        from_attributes = True


class AccountActivation(VerificationBase):
    """Schema for activating a pending account"""
    plan_id: str


# --- User schemas ---

class UserCreate(UserCredentialsBase):
    """Schema for creating a user (admin use)"""
    # UserCredentialsBase already includes all necessary fields


class UserUpdate(BaseModel):
    """Schema for updating user information - all fields optional"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    
    class Config:
        # Allow partial updates
        extra = "ignore"
        from_attributes = True
        
    @classmethod
    def from_user_base(cls, user: UserBase):
        """Create an update schema from a UserBase instance"""
        return cls(
            username=user.username,
            email=user.email,
            company=user.company
        )


class UserResponse(BaseModel):
    """
    Unified user response schema for API responses.
    Enhanced version that combines fields from previous UserResponse and UserProfile schemas.
    Contains all essential user information including IDs for editing and subscription details.
    """
    id: int
    username: str
    email: Optional[str] = None  # Use str instead of EmailStr to avoid validation
    company: Optional[str] = None
    is_active: bool
    subscription_status: str
    subscription_plan: Optional[str] = None
    subscription_id: Optional[str] = None
    payment_method_id: Optional[str] = None
    subscription_end_date: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# --- Admin schemas ---

class AdminUserCreate(UserCredentialsBase):
    """Schema for administrators to create user accounts"""
    # UserCredentialsBase already includes all required fields
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "interviewer1",
                "password": "securePassword123",
                "email": "interviewer@example.com",
                "company": "Example Corp"
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


class AdminUserResponse(BaseModel):
    """Extended user response schema with admin-relevant fields"""
    username: str
    email: Optional[str] = None  # Use str instead of EmailStr to avoid validation
    company: Optional[str] = None
    subscription_status: str
    subscription_plan: Optional[str] = None
    subscription_end_date: Optional[datetime] = None
    subscription_id: Optional[str] = None
    payment_method_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AdminUserUpdate(BaseModel):
    """Schema for admin to update user accounts"""
    # Basic information (no username update allowed)
    email: Optional[str] = None
    company: Optional[str] = None
    
    # Account access control
    is_active: Optional[bool] = None  # Controls login ability
    
    # Subscription details
    subscription_plan: Optional[str] = None
    subscription_end_date: Optional[datetime] = None
    subscription_status: Optional[str] = None  # active, expired, suspended, cancelled
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_active": True,
                "subscription_status": "active",
                "subscription_plan": "premium",
                "subscription_end_date": "2025-12-31T23:59:59"
            }
        }


# --- Admin authentication schemas ---

class AdminLogin(BaseModel):
    """Schema for admin login"""
    username: str
    password: str


class AdminCreate(BaseModel):
    """Schema for creating an admin account"""
    username: str
    password: str
    email: EmailStr
    full_name: Optional[str] = None


class AdminResponse(BaseModel):
    """Schema for admin response"""
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    
    class Config:
        from_attributes = True


class AdminUpdate(BaseModel):
    """Schema for updating admin information"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class AdminToken(BaseModel):
    """Schema for admin JWT token"""
    access_token: str
    token_type: str = "bearer"
    admin_id: int
    username: str


# Deprecated - use UserResponse instead
class UserProfile(UserBase, SubscriptionBase):
    """
    @deprecated: Use UserResponse instead.
    Kept for backward compatibility but will be removed in a future version.
    """
    id: int
    is_active: bool
    subscription_status: str
    subscription_id: Optional[str] = None
    payment_method_id: Optional[str] = None
    subscription_end_date: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

