"""
Endpoints for analyzing interview data.
"""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.api.dependencies import db_dependency, active_user_dependency
from app.core.database.models import User
from app.schemas.analytics_schemas import (
    InterviewStatsResponse, 
    DashboardResponse,
    TrendResponse,
    CandidatePerformanceBase,
    PaginatedResponse,
    InterviewAnalyticsResponse,
    SimpleAnalyticsResponse
)
from app.schemas.base_schemas import PaginationParams
from app.services.reporting.reporting_service import ReportingService

# Create router with Interviewer Panel tag instead of Analytics
router = APIRouter(tags=["Interviewer Panel"])


@router.get("", response_model=SimpleAnalyticsResponse)
def get_analytics(
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """
    Get simplified analytics data for the current interviewer.
    
    This endpoint provides basic analytics for the logged-in interviewer:
    - Summary statistics like total interviews, completion rate, etc.
    - Indication of recent activity in the past 24 hours
    
    Returns:
        SimpleAnalyticsResponse: Simplified analytics data with only essential metrics    """    # Initialize the reporting service
    reporting_service = ReportingService(db)
    
    # Get basic interview statistics
    stats = reporting_service.get_interview_stats()
    
    # Return simplified analytics response
    return SimpleAnalyticsResponse(
        total_interviews=stats.total_interviews,
        total_active_tokens=0,  # Would need token count logic
        completed_sessions=stats.completed_interviews,
        completion_rate=stats.completion_rate,
        has_recent_activity=stats.total_interviews > 0,  # Simplified check
        recent_sessions_count=0  # Would need recent session logic
    )
