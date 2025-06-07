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
from backup.analytics_service import AnalyticsService

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
        SimpleAnalyticsResponse: Simplified analytics data with only essential metrics
    """    # Initialize the analytics service
    analytics_service = AnalyticsService(db)
    # Get simplified analytics data for the current interviewer
    return analytics_service.get_simplified_analytics(interviewer_id=current_user.id)
