"""
Services package for the Interview Management Platform.

This package contains business logic services organized by domain,
following Domain-Driven Design principles to separate API handlers from core business logic.

Services are organized by domain:
- interviews: Interview flow and session management
- recordings: Recording upload and processing
- analysis: Interview response analysis and insights
- reporting: Analytics and report generation
- storage: File storage and management
"""

# Core service imports
from app.services.recordings.recording_service import RecordingService
from app.services.interviews.session_service import SessionService
from app.services.interviews.verification_service import VerificationService
# from app.services.analysis.analysis_service import AnalysisService  # Temporarily commented due to import issue
from app.services.reporting.reporting_service import ReportingService
from app.services.storage.storage_factory import get_storage
from app.services.storage.storage_adapter import StorageAdapter
from app.services.storage.s3_storage import S3Storage
from app.services.storage.local_storage import LocalStorage

__all__ = [
    # Interview management
    "SessionService",
    "VerificationService",
    
    # Recording handling
    "RecordingService",
    
    # Analysis and reporting
    "AnalysisService",
    "ReportingService",
    
    # Storage
    "StorageAdapter",
    "S3Storage", 
    "LocalStorage",
    "get_storage"
]