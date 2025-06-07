"""
Payments domain package.
Contains endpoints for payment processing, subscriptions, and webhook handling.
"""

from app.api.endpoints.payments.subscription import payment_router
from app.api.endpoints.payments.payment_router import router

__all__ = [
    "payment_router",           # Main router for all payment operations
    "router"                    # Alias for payment_router (for backward compatibility)
]