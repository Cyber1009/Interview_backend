"""
Payment and subscription related schemas.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.schemas.base_schemas import (
    UserBase,
    SubscriptionBase,
    EntityBase,
    VerificationBase
)

# --- Subscription Time Schemas ---

class SubscriptionTimeBase(BaseModel):
    """Base schema for subscription time information"""
    subscription_end_date: datetime


# --- Webhook Event Schemas ---

class WebhookEvent(BaseModel):
    """Schema for incoming webhook events from payment provider"""
    id: str
    type: str
    data: Dict[str, Any]
    created: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "evt_123456",
                "type": "customer.subscription.created",
                "data": {"object": {"id": "sub_123456"}},
                "created": 1609459200
            }
        }


# --- Registration and Payment Flow Schemas ---

class RegistrationCheckout(VerificationBase):
    """Schema for initiating checkout during registration"""
    plan_id: str


class RegistrationComplete(VerificationBase):
    """Schema for completing registration after checkout"""
    session_id: str


# --- Checkout Response Schemas ---

class CheckoutSession(BaseModel):
    """Schema for checkout session response"""
    checkout_url: str
    session_id: str


class CustomerPortalSession(BaseModel):
    """Schema for customer portal session"""
    portal_url: str


# --- Subscription Management Schemas ---

class SubscriptionCreate(BaseModel):
    """Schema for creating a new subscription"""
    user_id: int
    subscription_id: str
    subscription_end_date: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "subscription_id": "sub_12345",
                "subscription_end_date": "2025-12-31T23:59:59"
            }
        }


class SubscriptionUpdate(SubscriptionTimeBase):
    """Schema for updating an existing subscription"""
    is_active: bool = True
    subscription_plan: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_active": True,
                "subscription_plan": "premium",
                "subscription_end_date": "2025-12-31T23:59:59"
            }
        }


class SubscriptionResponse(SubscriptionTimeBase):
    """Schema for subscription details response"""
    user_id: int
    username: str
    company: Optional[str] = None
    subscription_id: str
    is_active: bool
    
    class Config:
        from_attributes = True


# --- Subscription Plan Schemas ---

class SubscriptionInfo(BaseModel):
    """Schema for current user subscription info"""
    plan_id: str
    plan_name: str
    active: bool
    end_date: Optional[datetime] = None
    status: str
    
    class Config:
        from_attributes = True


class SubscriptionPlanFeatures(BaseModel):
    """Base schema for subscription plan features"""
    name: str
    price_id: str
    duration: str = "monthly"
    duration_days: int = 30
    features: List[str]


class SubscriptionPlanList(BaseModel):
    """Schema for listing all available subscription plans"""
    basic: SubscriptionPlanFeatures
    premium: SubscriptionPlanFeatures
    enterprise: SubscriptionPlanFeatures