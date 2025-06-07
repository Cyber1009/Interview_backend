"""
Main router for payment-related endpoints.
"""
from fastapi import APIRouter
from .subscription import payment_router

# Export the consolidated payment router as the main router for the payments module
router = payment_router

__all__ = ["router"]