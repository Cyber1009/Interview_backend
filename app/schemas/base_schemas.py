"""
Core base schemas for the Interview Management Platform.

This module contains foundational schema classes that are widely used 
across different domain schemas in the application.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime

# --- Common Core Base Schemas ---

class TimestampBase(BaseModel):
    """Base schema for models with timestamp information"""
    created_at: datetime
    updated_at: Optional[datetime] = None


class EntityBase(BaseModel):
    """Base schema for entities with IDs"""
    id: int


# --- User Related Base Schemas ---

class UserBase(BaseModel):
    """Base schema with core user attributes that all user-related schemas should inherit"""
    username: str
    email: Optional[EmailStr] = None
    company: Optional[str] = None


class UserCredentialsBase(UserBase):
    """Base schema for any credential-based authentication"""
    password: str


# --- Subscription Base Schemas ---

class SubscriptionBase(BaseModel):
    """Base schema for subscription information"""
    is_active: bool = False
    subscription_plan: Optional[str] = None
    subscription_end_date: Optional[datetime] = None


# --- Token Base Schemas ---

class VerificationBase(BaseModel):
    """Base schema for verification processes"""
    verification_token: str


class CandidateTokenBase(BaseModel):
    """Base schema for candidate token operations"""
    token: str


# --- Pagination Base Schemas ---

T = TypeVar('T')

class PaginationParams(BaseModel):
    """
    Query parameters for pagination.
    Used across the application for consistent pagination behavior.
    """
    page: int = Field(1, description="Page number, starting from 1", ge=1)
    limit: int = Field(10, description="Number of items per page", ge=1, le=100)


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    total: int
    page: int
    limit: int
    pages: int
