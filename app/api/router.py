"""
Main router for API.
Organizes all endpoints into a cohesive API with clear domain separation by user role and resources.
"""
from fastapi import APIRouter

# Import consolidated router from interviewer domain
from app.api.endpoints.interviewer import router as interviewer_router
# Import authentication and registration routers from auth domain
from app.api.endpoints.auth.auth import auth_router
from app.api.endpoints.auth.registration import registration_router

# Import consolidated router from admin domain
from app.api.endpoints.admin import router as admin_router

# Import consolidated router from candidates domain
from app.api.endpoints.candidates import router as candidates_router

# Import consolidated router from payments domain
from app.api.endpoints.payments.payment_router import router as payment_router

# Create the main API router
api_router = APIRouter()

# =========================================================
# RESTRUCTURED ENDPOINT ORGANIZATION FOR BETTER SWAGGER UI
# =========================================================

# User Authentication tag - login, registration
api_router.include_router(auth_router, prefix="/auth", tags=["User"])
api_router.include_router(registration_router, prefix="/auth/registration", tags=["User"])

# Interviewer Panel tag - use consolidated interviewer router (includes bulk operations)
api_router.include_router(interviewer_router, prefix="/interviewer", tags=["Interviewer Panel"])

# Candidate Portal tag - all candidate-facing functionality with simplified paths
# Note: Batch processing for candidates is now included within the candidates router
api_router.include_router(candidates_router, prefix="/candidates", tags=["Candidate Portal"])

# Admin endpoints - use consolidated admin router
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])

# Billing and Subscriptions tag - consolidated payment endpoints
api_router.include_router(payment_router, prefix="/billing", tags=["Billing"])