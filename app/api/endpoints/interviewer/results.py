"""
Endpoints for handling interview results.
"""
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
import logging

from app.api.deps import db_dependency, active_user_dependency
from app.core.database.models import User, Interview, CandidateSession, Recording, Token
from app.schemas import InterviewResult
from app.utils.error_utils import not_found, forbidden

# Create router
results_router = APIRouter()

@results_router.get("/{interview_id}/results", response_model=List[InterviewResult])
def get_interview_results(
    interview_id: int,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Get results for a specific interview"""
    # Verify interview exists and belongs to user
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.owner_id == current_user.id
    ).first()
    
    if not interview:
        not_found("Interview", interview_id)
    
    # Use a join to efficiently get sessions and their tokens in a single query
    sessions = (db.query(CandidateSession)
                .join(Token, CandidateSession.token_id == Token.id)
                .filter(Token.interview_id == interview_id)
                .all())
    
    results = []
    for session in sessions:
        # Get recordings for this session
        recordings = db.query(Recording).filter(Recording.session_id == session.id).all()
        
        # Get token for this session - we can access it directly through the relationship
        token = db.query(Token).filter(Token.id == session.token_id).first()
        
        result = InterviewResult(
            session_id=session.id,
            token_value=token.token_value,
            start_time=session.start_time,
            end_time=session.end_time,
            recordings=recordings
        )
        
        results.append(result)
    
    return results

@results_router.get("/", response_model=List[InterviewResult])
def get_all_results(
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Get results for all interviews owned by the current user"""
    # Use more efficient joins to get all the data in fewer queries
    sessions = (db.query(CandidateSession)
                .join(Token, CandidateSession.token_id == Token.id)
                .join(Interview, Token.interview_id == Interview.id)
                .filter(Interview.owner_id == current_user.id)
                .all())
    
    results = []
    for session in sessions:
        # Get recordings for this session
        recordings = db.query(Recording).filter(Recording.session_id == session.id).all()
        
        # Get token for this session
        token = db.query(Token).filter(Token.id == session.token_id).first()
        
        result = InterviewResult(
            session_id=session.id,
            token_value=token.token_value,
            start_time=session.start_time,
            end_time=session.end_time,
            recordings=recordings
        )
        
        results.append(result)
    
    return results

@results_router.delete("/{interview_id}/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_interview_result(
    interview_id: int,
    session_id: int,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Delete a specific interview result (session)"""
    # Verify interview exists and belongs to user
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.owner_id == current_user.id
    ).first()
    
    if not interview:
        not_found("Interview", interview_id)
    
    # Use a join to efficiently verify the relationship in one query
    session = (db.query(CandidateSession)
               .join(Token, CandidateSession.token_id == Token.id)
               .filter(
                   CandidateSession.id == session_id,
                   Token.interview_id == interview_id
               ).first())
    
    if not session:
        not_found("Session", session_id)
    
    # Delete all recordings for this session
    db.query(Recording).filter(Recording.session_id == session_id).delete()
    
    # Delete the session
    db.delete(session)
    db.commit()
    
    return None