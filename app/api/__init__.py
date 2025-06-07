"""
API package for the Interview Management Platform.

This package exposes:
1. The main API router that ties together all endpoints
2. Dependencies for authentication, database sessions, and services
3. Domain-specific endpoint modules
"""
# Note: api_router import removed to prevent circular imports
# Import api_router directly from app.api.router when needed

# Import all dependencies from the consolidated dependencies module
from app.api.dependencies import (
    # Database dependencies
    db_dependency,
    
    # Authentication dependencies
    user_dependency, 
    active_user_dependency,
    interviewer_dependency,
    admin_dependency,
    get_current_user,
    
    # Service dependencies
    verification_service_dependency,
    session_service_dependency,
    recording_service_dependency,
    reporting_service_dependency,
    content_analysis_service_dependency,
    transcription_service_dependency,
    get_reporting_service
)

__all__ = [
    # Database dependencies
    "db_dependency",
    
    # Authentication dependencies
    "user_dependency",
    "active_user_dependency",
    "interviewer_dependency",
    "admin_dependency",
    "get_current_user",
    
    # Service dependencies
    "verification_service_dependency",
    "session_service_dependency",
    "recording_service_dependency",
    "reporting_service_dependency",
    "content_analysis_service_dependency",
    "transcription_service_dependency",
    "get_reporting_service"
]