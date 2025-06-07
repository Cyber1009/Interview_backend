"""
Consolidated API Dependencies Module

This module consolidates all dependencies used throughout the application:
- Database session dependencies
- Authentication dependencies  
- Service dependencies
- All previously scattered dependency patterns

By centralizing dependencies, we ensure consistent dependency injection patterns
and make it easier to modify dependencies across the application.
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Generator

# Database imports
from app.core.database.db import get_db

# Authentication imports
from app.core.database.models import User, Admin
from app.core.security.auth import (
    get_current_user,
    check_subscription_status,
    oauth2_scheme,
    get_current_admin
)

# Service imports
from app.services.interviews.verification_service import VerificationService
from app.services.interviews.session_service import SessionService
from app.services.recordings.recording_service import RecordingService
from app.services.reporting.reporting_service import ReportingService
from app.services.analysis.analysis_service import AnalysisService
from app.services.transcription.transcription_service import TranscriptionService
from app.services.analytics.analytics_service import AnalyticsService

# ============================================================================
# Database Dependencies
# ============================================================================

db_dependency = Depends(get_db)

# ============================================================================
# Authentication Dependencies
# ============================================================================

# Basic user dependency - verified JWT token
user_dependency = Depends(get_current_user)

# Admin dependency
admin_dependency = Depends(get_current_admin)

# Middleware to check if user's subscription is active
def get_active_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify user has an active subscription.
    
    This middleware only checks if the subscription is active 
    using the status that was already updated in get_current_user.
    """
    # No need to call check_subscription_status again as it's already done in get_current_user
    # Just verify the current status
    if not current_user.is_active or current_user.subscription_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscription inactive or expired. Please renew your subscription."
        )
    
    return current_user

# Active user dependency 
active_user_dependency = Depends(get_active_user)

# Role-specific dependencies - making it clear which endpoints require which roles
interviewer_dependency = active_user_dependency  # Interviewers need active subscriptions

# ============================================================================
# Service Dependencies
# ============================================================================

# Content processing services
def get_transcription_service() -> UnifiedTranscriptionService:
    """Dependency for getting a UnifiedTranscriptionService instance."""
    return UnifiedTranscriptionService()

def get_content_analysis_service() -> ContentAnalysisService:
    """Dependency for getting a ContentAnalysisService instance."""
    return ContentAnalysisService()

# Core business services
def get_recording_service(
    transcription_service: UnifiedTranscriptionService = Depends(get_transcription_service),
    analysis_service: ContentAnalysisService = Depends(get_content_analysis_service)
) -> RecordingService:
    """Dependency for getting a RecordingService instance."""
    return RecordingService(
        transcription_service=transcription_service,
        analysis_service=analysis_service
    )

def get_session_service() -> SessionService:
    """Dependency for getting a SessionService instance."""
    return SessionService()

def get_verification_service() -> VerificationService:
    """Dependency for getting a VerificationService instance."""
    return VerificationService()

def get_reporting_service(db: Session = Depends(get_db)) -> ReportingService:
    """Dependency for getting a ReportingService instance."""
    return ReportingService(db)

def get_analytics_service(db: Session = Depends(get_db)) -> AnalyticsService:
    """Dependency for getting an AnalyticsService instance."""
    return AnalyticsService(db)

def get_optimized_url_service() -> OptimizedRecordingUrlService:
    """Dependency for getting an OptimizedRecordingUrlService instance."""
    return OptimizedRecordingUrlService()

def get_smart_retry_service() -> SmartRetryService:
    """Dependency for getting a SmartRetryService instance."""
    return SmartRetryService()

# Service dependencies - for use with Depends()
transcription_service_dependency = Depends(get_transcription_service)
content_analysis_service_dependency = Depends(get_content_analysis_service)
recording_service_dependency = Depends(get_recording_service)
session_service_dependency = Depends(get_session_service)
verification_service_dependency = Depends(get_verification_service)
reporting_service_dependency = Depends(get_reporting_service)
analytics_service_dependency = Depends(get_analytics_service)
optimized_url_service_dependency = Depends(get_optimized_url_service)
smart_retry_service_dependency = Depends(get_smart_retry_service)

# ============================================================================
# Convenience Dependencies (Backward Compatibility)
# ============================================================================

# For backward compatibility with existing code
active_subscription_dependency = active_user_dependency
get_current_active_user = get_active_user
