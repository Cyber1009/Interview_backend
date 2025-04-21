"""
Endpoints for interview management by interviewers.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import db_dependency, active_user_dependency
# Fix import path for models
from app.core.database.models import User, Interview, CandidateSession, Recording, Token
from app.schemas import InterviewCreate, InterviewResponse
from app.utils.error_utils import not_found, forbidden, bad_request

# Create router
interviews_router = APIRouter()

@interviews_router.get("/", response_model=List[InterviewResponse])
def get_all_interviews(
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Get all interviews for the current interviewer"""
    interviews = db.query(Interview).filter(
        Interview.owner_id == current_user.id
    ).all()
    
    return interviews

@interviews_router.post("/", response_model=InterviewResponse)
def create_interview(
    interview: InterviewCreate,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Create a new interview"""
    db_interview = Interview(
        title=interview.title,
        owner_id=current_user.id
    )
    
    db.add(db_interview)
    db.commit()
    db.refresh(db_interview)
    
    return db_interview

@interviews_router.get("/{interview_id}", response_model=InterviewResponse)
def get_interview(
    interview_id: int,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Get a specific interview with all its questions"""
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.owner_id == current_user.id
    ).first()
    
    if not interview:
        not_found("Interview", interview_id)
    
    return interview

@interviews_router.put("/{interview_id}", response_model=InterviewResponse)
def update_interview(
    interview_id: int,
    interview_update: InterviewCreate,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Update an interview's title"""
    interview = db.query(Interview).filter(
        Interview.id == interview_id
    ).first()
    
    if not interview:
        not_found("Interview", interview_id)
        
    if interview.owner_id != current_user.id:
        forbidden("You don't have permission to update this interview")
    
    interview.title = interview_update.title
    
    db.commit()
    db.refresh(interview)
    
    return interview

@interviews_router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_interview(
    interview_id: int,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Delete an interview and all associated questions and tokens"""
    interview = db.query(Interview).filter(
        Interview.id == interview_id
    ).first()
    
    if not interview:
        not_found("Interview", interview_id)
        
    if interview.owner_id != current_user.id:
        forbidden("You don't have permission to delete this interview")
    
    db.delete(interview)
    db.commit()
    
    return None

@interviews_router.delete("/{interview_id}/results/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
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