"""
Interview analytics schemas for the application.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Generic, TypeVar
from datetime import datetime, date

from app.schemas.base_schemas import EntityBase, TimestampBase


class InterviewStatsBase(BaseModel):
    """Base schema for interview statistics"""
    total_interviews: int
    completed_interviews: int
    completion_rate: float
    avg_duration_seconds: Optional[float] = None


class CandidatePerformanceBase(BaseModel):
    """Base schema for candidate performance metrics"""
    interview_id: int
    candidate_id: int
    score: Optional[float] = None
    duration_seconds: Optional[float] = None
    questions_answered: int
    total_questions: int
    completion_percentage: float


class InterviewTrendPoint(BaseModel):
    """Schema for a single point in trend analysis"""
    date: date
    count: int
    completion_rate: Optional[float] = None


class InterviewTrendsBase(BaseModel):
    """Base schema for interview trend analysis"""
    period: str = Field(..., description="Period for trend analysis: 'daily', 'weekly', or 'monthly'")
    trends: List[InterviewTrendPoint]


class InterviewStatsResponse(InterviewStatsBase):
    """Response schema for interview statistics with additional metrics"""
    avg_questions_per_interview: Optional[float] = None
    avg_score: Optional[float] = None
    recent_interviews_count: Optional[int] = None
    
    class Config:
        from_attributes = True


class TrendResponse(InterviewTrendsBase):
    """Response schema for trend analysis with additional metrics"""
    total_period_count: int
    
    class Config:
        from_attributes = True


T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic schema for paginated responses"""
    items: List[T]
    total: int
    page: int
    limit: int
    
    class Config:
        from_attributes = True


class DashboardResponse(BaseModel):
    """Schema for comprehensive dashboard analytics"""
    stats: InterviewStatsResponse
    trends: TrendResponse
    performance_metrics: List[CandidatePerformanceBase]
    performance_pagination: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class SimpleAnalyticsResponse(BaseModel):
    """Simplified analytics response with only essential metrics"""
    total_interviews: int
    total_active_tokens: int
    completed_sessions: int
    completion_rate: float
    has_recent_activity: bool
    recent_sessions_count: int
    
    class Config:
        from_attributes = True


class InterviewAnalyticsResponse(BaseModel):
    """Combined analytics response schema with pagination support"""
    stats: InterviewStatsBase
    trends: InterviewTrendsBase = None
    performance_metrics: List[CandidatePerformanceBase] = []
    performance_pagination: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
