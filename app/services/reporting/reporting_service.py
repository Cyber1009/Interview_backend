"""
Service for handling interview reporting and analytics operations.
"""
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date, timedelta
import calendar
from sqlalchemy import func, and_, desc
from sqlalchemy.orm import Session

from app.core.database.db import get_db
from app.core.database.models import Interview, Recording, CandidateSession, Token
from app.schemas.analytics_schemas import (
    InterviewStatsBase, 
    CandidatePerformanceBase,
    InterviewTrendPoint,
    InterviewTrendsBase
)


class ReportingService:
    """Service for handling interview reporting and analytics operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_interview_stats(self) -> InterviewStatsBase:
        """
        Get summary statistics for interviews.
        
        Returns:
            InterviewStatsBase: Interview summary statistics
        """
        # Get total interviews
        total_interviews = self.db.query(Interview).count()
        
        # Calculate completed interviews
        # Since there's no 'completed' field in Interview, we'll determine it by checking 
        # if all questions have recordings with end_time set
        subq = (
            self.db.query(
                Interview.id,
                func.count(func.distinct(Recording.question_id)).label("answered_questions"),
                func.count(func.distinct(Interview.questions)).label("total_questions")
            )
            .join(Interview.questions)
            .join(Recording, Recording.question_id == Interview.questions.id)
            .filter(Recording.end_time.isnot(None))
            .group_by(Interview.id)
            .subquery()
        )
        
        completed_interviews = (
            self.db.query(func.count())
            .select_from(subq)
            .filter(subq.c.answered_questions == subq.c.total_questions)
            .scalar() or 0
        )
        
        # Calculate completion rate
        completion_rate = 0.0
        if total_interviews > 0:
            completion_rate = round(completed_interviews / total_interviews * 100, 2)
        
        # Calculate average duration
        avg_duration = self.db.query(
            func.avg(func.extract('epoch', Recording.end_time - Recording.start_time))
        ).filter(Recording.end_time.isnot(None)).scalar()
        
        return InterviewStatsBase(
            total_interviews=total_interviews,
            completed_interviews=completed_interviews,
            completion_rate=completion_rate,
            avg_duration_seconds=avg_duration
        )

    def get_candidate_performance(self, page: int = 1, limit: int = 10) -> Tuple[List[CandidatePerformanceBase], int]:
        """
        Get performance metrics for candidates.
        
        Args:
            page: Page number (starting from 1)
            limit: Number of items per page
            
        Returns:
            Tuple[List[CandidatePerformanceBase], int]: Candidate performance metrics and total count
        """
        # Query for candidate performance - using CandidateSession instead of Candidate
        query = (
            self.db.query(
                Interview.id.label("interview_id"),
                CandidateSession.id.label("session_id"),
                func.count(Recording.id).label("questions_answered"),
                func.count(Interview.questions).label("total_questions")
            )
            .join(Token, Token.interview_id == Interview.id)
            .join(CandidateSession, CandidateSession.token_id == Token.id)
            .outerjoin(Recording, and_(
                Recording.session_id == CandidateSession.id,
                Recording.end_time.isnot(None)
            ))
            .group_by(Interview.id, CandidateSession.id)
        )
        
        # Calculate total for pagination
        total = query.count()
        
        # Apply pagination
        query = query.offset((page - 1) * limit).limit(limit)
        
        # Build candidate performance metrics
        result = []
        for row in query.all():
            completion_percentage = 0.0
            if row.total_questions > 0:
                completion_percentage = round(row.questions_answered / row.total_questions * 100, 2)
            
            # Get average duration for this session's recordings
            avg_duration = (
                self.db.query(func.avg(func.extract('epoch', Recording.end_time - Recording.start_time)))
                .filter(
                    Recording.session_id == row.session_id,
                    Recording.end_time.isnot(None)
                )
                .scalar()
            )
            
            result.append(CandidatePerformanceBase(
                interview_id=row.interview_id,
                candidate_id=row.session_id,  # Using session_id instead of candidate_id
                duration_seconds=avg_duration,
                score=None,  # Score calculation could be added in the future
                questions_answered=row.questions_answered,
                total_questions=row.total_questions,
                completion_percentage=completion_percentage
            ))
        
        return result, total

    def get_interview_trends(self, period: str = "weekly", days: int = 30) -> InterviewTrendsBase:
        """
        Get trend analysis for interviews over time.
        
        Args:
            period: Period for trend analysis ('daily', 'weekly', or 'monthly')
            days: Number of days to analyze
            
        Returns:
            InterviewTrendsBase: Interview trend analysis
        """
        today = datetime.today().date()
        start_date = today - timedelta(days=days)
        
        # Base query for interviews by date
        date_trunc_sql = "date_trunc('day', created_at)"
        if period == "weekly":
            date_trunc_sql = "date_trunc('week', created_at)"
        elif period == "monthly":
            date_trunc_sql = "date_trunc('month', created_at)"
        
        # Get interview counts by date
        date_counts = (
            self.db.query(
                func.cast(func.date(func.text(date_trunc_sql)), date).label("date"),
                func.count(Interview.id).label("count")
            )
            .filter(func.date(Interview.created_at) >= start_date)
            .group_by(func.text("date"))
            .order_by(func.text("date"))
            .all()
        )
        
        # Calculate completion rate for each date
        trend_points = []
        for point in date_counts:
            # For each date, find interviews and their completion status
            interviews_on_date = (
                self.db.query(Interview.id)
                .filter(func.date(func.text(date_trunc_sql)) == point.date)
                .all()
            )
            
            interview_ids = [i.id for i in interviews_on_date]
            
            if interview_ids:
                # Count recordings with end_time set for these interviews
                completion_data = (
                    self.db.query(
                        Interview.id,
                        func.count(func.distinct(Recording.question_id)).label("answered"),
                        func.count(func.distinct(Interview.questions)).label("total")
                    )
                    .join(Interview.questions)
                    .outerjoin(Recording, and_(
                        Recording.question_id == Interview.questions.c.id,
                        Recording.end_time.isnot(None)
                    ))
                    .filter(Interview.id.in_(interview_ids))
                    .group_by(Interview.id)
                    .all()
                )
                
                # Calculate completion rate
                completed = sum(1 for i in completion_data if i.answered >= i.total)
                completion_rate = round((completed / len(interview_ids)) * 100, 2) if interview_ids else None
            else:
                completion_rate = None
                
            trend_points.append(InterviewTrendPoint(
                date=point.date,
                count=point.count,
                completion_rate=completion_rate
            ))
        
        return InterviewTrendsBase(
            period=period,
            trends=trend_points
        )