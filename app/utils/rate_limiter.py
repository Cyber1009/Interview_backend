"""
Rate limiter utilities for API rate limiting.

This module provides functionality to limit API request rates per user/client.
"""
from fastapi import Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Callable, Dict, Any, Optional
from functools import wraps
import logging
from enum import Enum, auto
import asyncio

logger = logging.getLogger(__name__)

class RateLimitType(str, Enum):
    """Enum defining different types of rate limits."""
    DEFAULT = "default"
    AUTH = "auth"
    SENSITIVE = "sensitive"
    REGISTRATION = "registration"
    API = "api"
    PAYMENT = "payment"
    ANALYTICS = "analytics"

# Create the rate limiter with a default key function
limiter = Limiter(key_func=get_remote_address)

# Define rate limit defaults
DEFAULT_RATE_LIMIT = "60/minute"  # Default rate limit for general endpoints
AUTH_RATE_LIMIT = "10/minute"     # More restrictive limit for auth endpoints
SENSITIVE_RATE_LIMIT = "30/minute"  # Moderate limit for sensitive operations

def get_client_identifier(request: Request) -> str:
    """
    Get a client identifier for rate limiting, with preference order:
    1. User ID from authentication (most reliable but requires auth)
    2. X-Forwarded-For header (when behind a proxy)
    3. Client's IP address (fallback)
    
    Args:
        request: The FastAPI request object
        
    Returns:
        String identifier for the client
    """
    # Check for authenticated user ID
    if hasattr(request.state, "user_id") and request.state.user_id:
        return f"user:{request.state.user_id}"
    
    # Get forwarded IP if behind a proxy
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Use the first IP in the chain to avoid spoofing
        client_ip = forwarded_for.split(",")[0].strip()
        return f"ip:{client_ip}"
    
    # Fallback to direct client IP
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"

# Custom key function to identify clients more reliably
def rate_limit_key_func(request: Request) -> str:
    """
    Key function for rate limiting that prioritizes authenticated user ID over IP address.
    
    Args:
        request: FastAPI request object
        
    Returns:
        String key for rate limiting
    """
    return get_client_identifier(request)

# Create an enhanced limiter that uses our custom key function
enhanced_limiter = Limiter(key_func=rate_limit_key_func)

def get_rate_limits(is_authenticated: bool, tier: Optional[str] = None) -> Dict[str, str]:
    """
    Get appropriate rate limits based on authentication status and subscription tier.
    
    Args:
        is_authenticated: Whether the user is authenticated
        tier: The user's subscription tier (if any)
        
    Returns:
        Dictionary mapping limit types to rate limit strings
    """
    # Unauthenticated users get the most restrictive limits
    if not is_authenticated:
        return {
            "default": "30/minute",
            "auth": "5/minute",
            "sensitive": "10/minute",
        }
    
    # Adjust limits based on subscription tier
    if tier == "premium":
        return {
            "default": "120/minute",
            "auth": "20/minute",
            "sensitive": "60/minute",
        }
    elif tier == "enterprise":
        return {
            "default": "300/minute",
            "auth": "30/minute", 
            "sensitive": "150/minute",
        }
    else:
        # Regular authenticated users
        return {
            "default": "60/minute",
            "auth": "10/minute",
            "sensitive": "30/minute",
        }

# Dynamic rate limiting decorator that adjusts limits based on user authentication/tier
def dynamic_rate_limit(limit_type: str = "default"):
    """
    Decorator for dynamically setting rate limits based on user authentication and tier.
    
    Args:
        limit_type: Type of limit to apply ("default", "auth", "sensitive", etc.)
    """
    def decorator(func: Callable) -> Callable:
        is_async = asyncio.iscoroutinefunction(func)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get the request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                for _, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if not request:
                logger.warning("Could not find request object in arguments")
                return await func(*args, **kwargs)
                
            # Determine if user is authenticated and their tier
            is_authenticated = hasattr(request.state, "user") and request.state.user is not None
            tier = getattr(request.state.user, "subscription_tier", None) if is_authenticated else None
            
            # Get appropriate rate limits
            limits = get_rate_limits(is_authenticated, tier)
            rate_limit = limits.get(limit_type, DEFAULT_RATE_LIMIT)
            
            # Set the rate limit key on the request for the middleware to pick up
            request.state.view_rate_limit = rate_limit
            request.state.view_rate_limit_key = rate_limit_key_func(request)
            
            # Execute the original function
            return await func(*args, **kwargs)
            
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Get the request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                for _, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if not request:
                logger.warning("Could not find request object in arguments")
                return func(*args, **kwargs)
                
            # Determine if user is authenticated and their tier
            is_authenticated = hasattr(request.state, "user") and request.state.user is not None
            tier = getattr(request.state.user, "subscription_tier", None) if is_authenticated else None
            
            # Get appropriate rate limits
            limits = get_rate_limits(is_authenticated, tier)
            rate_limit = limits.get(limit_type, DEFAULT_RATE_LIMIT)
            
            # Set the rate limit key on the request for the middleware to pick up
            request.state.view_rate_limit = rate_limit
            request.state.view_rate_limit_key = rate_limit_key_func(request)
            
            # Execute the original function
            return func(*args, **kwargs)
            
        # Return the appropriate wrapper based on whether the function is async or not
        return async_wrapper if is_async else sync_wrapper
    
    return decorator