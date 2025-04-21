"""
Main router for API.
Organizes all endpoints into a cohesive API with clear domain separation by user role and resources.
"""
from fastapi import APIRouter

# Import routers from interviewer domain
from app.api.endpoints.interviewer.interviews import interviews_router
from app.api.endpoints.interviewer.questions import questions_router
from app.api.endpoints.interviewer.tokens import tokens_router
from app.api.endpoints.interviewer.results import results_router
from app.api.endpoints.interviewer.theme import theme_router

# Import routers from auth domain
from app.api.endpoints.auth.auth import auth_router
from app.api.endpoints.auth.registration import registration_router

# Import routers from candidates domain
from app.api.endpoints.candidates.candidates import candidates_router

# Import routers from admin domain
from app.api.endpoints.admin.admin import admin_router
from app.api.endpoints.admin.accounts import accounts_router

# Import routers from payments domain
from app.api.endpoints.payments.checkout import checkout_router
from app.api.endpoints.payments.webhook import webhook_router

# Import router from system domain
from app.api.endpoints.system import system_router

# Create the main API router
api_router = APIRouter()

# Authentication domain
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(registration_router, prefix="/auth/registration", tags=["Authentication"])

# Interviewer domain - RESTful resource-based organization
api_router.include_router(interviews_router, prefix="/interviewer/interviews", tags=["Interviewer"])
api_router.include_router(questions_router, prefix="/interviewer/interviews", tags=["Interviewer"])
api_router.include_router(tokens_router, prefix="/interviewer/interviews", tags=["Interviewer"])
api_router.include_router(results_router, prefix="/interviewer/results", tags=["Interviewer"])
api_router.include_router(theme_router, prefix="/interviewer/profile/theme", tags=["Interviewer"])

# Candidate domain - for interview participants
api_router.include_router(candidates_router, prefix="/candidates", tags=["Candidates"])

# Payment and subscription domain
api_router.include_router(checkout_router, prefix="/payments/checkout", tags=["Payments"])
api_router.include_router(webhook_router, prefix="/payments/webhook", tags=["Payments"])

# Admin domain - clearly separated but with unified tag
api_router.include_router(admin_router, prefix="/admin/system", tags=["Administration"])
api_router.include_router(accounts_router, prefix="/admin/users", tags=["Administration"])

# System domain - health checks and monitoring
api_router.include_router(system_router, prefix="/system", tags=["System"])