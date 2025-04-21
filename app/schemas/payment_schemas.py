"""
Payment and subscription related schemas.
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

# Webhook Event Schema
class WebhookEvent(BaseModel):
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

# Registration and Payment Flow Schemas
class UserRegistration(BaseModel):
    username: str
    password: str
    email: str
    company_name: Optional[str] = None

class RegistrationCheckout(BaseModel):
    verification_token: str
    plan_id: str

class RegistrationComplete(BaseModel):
    verification_token: str
    session_id: str

class StripeCheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str

# Subscription Management Schemas
class SubscriptionCreate(BaseModel):
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

class SubscriptionUpdate(BaseModel):
    subscription_end_date: datetime
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

class SubscriptionResponse(BaseModel):
    user_id: int
    username: str
    company_name: Optional[str] = None
    subscription_id: str
    subscription_end_date: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

# Subscription & Payment Schemas
class SubscriptionInfo(BaseModel):
    plan_id: str
    plan_name: str
    active: bool
    end_date: Optional[datetime] = None
    status: str
    
    class Config:
        from_attributes = True

class CheckoutSession(BaseModel):
    checkout_url: str
    session_id: str

class CustomerPortalSession(BaseModel):
    portal_url: str

class SubscriptionPlan(BaseModel):
    name: str
    price_id: str
    duration: Optional[str] = "monthly"
    duration_days: Optional[int] = 30
    features: List[str]

class SubscriptionPlanList(BaseModel):
    basic: SubscriptionPlan
    premium: SubscriptionPlan
    enterprise: SubscriptionPlan