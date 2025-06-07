"""
Interview management endpoints.
Consolidated module that combines interview creation, question management, and token generation.
"""
from fastapi import APIRouter, HTTPException, status, File, UploadFile, Body, Path
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Union, Any
from enum import Enum
import secrets
import string

from app.api.dependencies import db_dependency, active_user_dependency
from app.core.database.models import User, Interview, Question, Token, CandidateSession, Recording
from app.schemas.interview_schemas import (
    InterviewBase, InterviewCreateWithQuestions, InterviewResponse, InterviewUpdateWithQuestions,
    QuestionBase, QuestionResponse, QuestionOrderUpdate, 
    CandidateTokenCreate, CandidateTokenResponse, InterviewListResponse
)
from app.api.exceptions import not_found, forbidden, bad_request
from app.core.database.repositories import InterviewRepository
from app.utils.interview_utils import get_interview_by_key

# Create unified router
router = APIRouter()

# ======================================================================
# SECTION: Interview Listing and Creation
# ======================================================================

@router.get("/interviews", response_model=List[InterviewListResponse])
def get_all_interviews(
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Get all interviews for the current interviewer"""
    interviews = db.query(Interview).filter(
        Interview.interviewer_id == current_user.id
    ).all()
    return interviews

@router.post("/interviews", response_model=InterviewResponse)
def create_interview(
    interview: InterviewCreateWithQuestions,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Create a new interview with optional questions"""
    # Create the interview
    db_interview = Interview(
        title=interview.title,
        interviewer_id=current_user.id
    )
    
    db.add(db_interview)
    db.commit()
    db.refresh(db_interview)
    
    # Add questions if provided
    if interview.questions:
        for i, question_data in enumerate(interview.questions):
            db_question = Question(
                interview_id=db_interview.id,
                text=question_data.text,
                preparation_time=question_data.preparation_time,
                responding_time=question_data.responding_time,
                order=i + 1
            )
            db.add(db_question)
        
        db.commit()
        # Refresh to get the questions
        db.refresh(db_interview)
    
    return db_interview

# ======================================================================
# SECTION: Individual Interview Operations
# ======================================================================

@router.get("/interviews/{interview_key}", response_model=InterviewResponse)
def get_interview(
    interview_key: str,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Get a specific interview with all its questions"""
    interview = get_interview_by_key(db, interview_key, current_user.id)
    return interview

@router.put("/interviews/{interview_key}", response_model=InterviewResponse)
def update_interview(
    interview_key: str,
    interview_update: InterviewBase,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Update an interview's title"""
    interview = get_interview_by_key(db, interview_key, current_user.id)
    
    interview.title = interview_update.title
    db.commit()
    db.refresh(interview)
    
    return interview

@router.delete("/interviews/{interview_key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_interview(
    interview_key: str,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Delete an interview and all associated questions and tokens"""
    interview = get_interview_by_key(db, interview_key, current_user.id)
    
    db.delete(interview)
    db.commit()
    
    return None

# ======================================================================
# SECTION: Question Management
# ======================================================================

@router.get("/interviews/{interview_key}/questions", response_model=List[QuestionResponse])
def get_questions(
    interview_key: str,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Get all questions for an interview"""
    interview = get_interview_by_key(db, interview_key, current_user.id)
    
    return db.query(Question).filter(
        Question.interview_id == interview.id
    ).order_by(Question.order).all()

@router.post("/interviews/{interview_key}/questions", response_model=QuestionResponse)
def create_question(
    interview_key: str,
    question: QuestionBase,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Add a new question to an interview"""
    interview = get_interview_by_key(db, interview_key, current_user.id)
    
    # Get the highest order number for this interview
    max_order = db.query(Question).filter(
        Question.interview_id == interview.id
    ).count()
    
    db_question = Question(
        interview_id=interview.id,
        text=question.text,
        order=max_order + 1
    )
    
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    
    return db_question

@router.put("/interviews/{interview_key}/questions/{question_id}", response_model=QuestionResponse)
def update_question(
    interview_key: str,
    question_id: int,
    question_update: QuestionBase,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Update a question"""
    interview = get_interview_by_key(db, interview_key, current_user.id)
    
    question = db.query(Question).filter(
        Question.id == question_id,
        Question.interview_id == interview.id
    ).first()
    
    if not question:
        not_found("Question", question_id)
    
    question.text = question_update.text
    db.commit()
    db.refresh(question)
    
    return question

@router.delete("/interviews/{interview_key}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    interview_key: str,
    question_id: int,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Delete a question from an interview"""
    interview = get_interview_by_key(db, interview_key, current_user.id)
    
    question = db.query(Question).filter(
        Question.id == question_id,
        Question.interview_id == interview.id
    ).first()
    
    if not question:
        not_found("Question", question_id)
    
    db.delete(question)
    db.commit()
    
    return None

@router.put("/interviews/{interview_key}/questions/reorder")
def reorder_questions(
    interview_key: str,
    question_orders: List[QuestionOrderUpdate],
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Reorder questions in an interview"""
    interview = get_interview_by_key(db, interview_key, current_user.id)
    
    for update in question_orders:
        question = db.query(Question).filter(
            Question.id == update.id,
            Question.interview_id == interview.id
        ).first()
        
        if question:
            question.order = update.order
    
    db.commit()
    return {"message": "Questions reordered successfully"}

# ======================================================================
# SECTION: Token Management
# ======================================================================

@router.get("/interviews/{interview_key}/tokens", response_model=List[CandidateTokenResponse])
def get_tokens(
    interview_key: str,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Get all tokens for an interview"""
    interview = get_interview_by_key(db, interview_key, current_user.id)
    
    return db.query(Token).filter(
        Token.interview_id == interview.id
    ).all()

@router.post("/interviews/{interview_key}/tokens", response_model=CandidateTokenResponse)
def create_token(
    interview_key: str,
    token_data: Optional[CandidateTokenCreate] = None,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Generate a new token for an interview with enhanced capabilities"""
    interview = get_interview_by_key(db, interview_key, current_user.id)
    
    # Generate random token
    token_value = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    # Set expiry time if provided
    expires_at = None
    if token_data and token_data.expires_in_hours:
        from datetime import datetime, timedelta
        expires_at = datetime.now() + timedelta(hours=token_data.expires_in_hours)
    
    # Set max attempts
    max_attempts = 1
    if token_data and token_data.max_attempts:
        max_attempts = token_data.max_attempts
    
    # Set candidate name
    candidate_name = None
    if token_data and token_data.candidate_name:
        candidate_name = token_data.candidate_name
    
    db_token = Token(
        interview_id=interview.id,
        token_value=token_value,
        candidate_name=candidate_name,
        expires_at=expires_at,
        max_attempts=max_attempts,
        current_attempts=0,
        is_used=False
    )
    
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    
    return db_token

@router.delete("/interviews/{interview_key}/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_token(
    interview_key: str,
    token_id: int,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Delete a token"""
    interview = get_interview_by_key(db, interview_key, current_user.id)
    
    token = db.query(Token).filter(
        Token.id == token_id,
        Token.interview_id == interview.id
    ).first()
    
    if not token:
        not_found("Token", token_id)
    
    db.delete(token)
    db.commit()
    
    return None

# ======================================================================
# SECTION: Bulk Operations
# ======================================================================

@router.put("/interviews/{interview_key}/update-with-questions", response_model=InterviewResponse)
def update_interview_with_questions(
    interview_key: str,
    interview_update: InterviewUpdateWithQuestions,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Update interview title and questions in one operation"""
    interview = get_interview_by_key(db, interview_key, current_user.id)
    
    # Update interview title
    if interview_update.title:
        interview.title = interview_update.title
    
    # Update questions if provided
    if interview_update.questions:
        # Delete existing questions
        db.query(Question).filter(Question.interview_id == interview.id).delete()
        
        # Add new questions
        for i, question_data in enumerate(interview_update.questions):
            db_question = Question(
                interview_id=interview.id,
                text=question_data.text,
                order=i + 1
            )
            db.add(db_question)
    
    db.commit()
    db.refresh(interview)
    
    return interview