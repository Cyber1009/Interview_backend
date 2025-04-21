"""
Endpoints for candidate session management.
Handles starting and completing interview sessions.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any

from app.api.deps import db_dependency
from app.core.database.models import Token, CandidateSession
from app.schemas.interview_schemas import SessionStart, SessionResponse
from app.utils.error_utils import not_found, bad_request

# Create router
sessions_router = APIRouter()

@sessions_router.post("/session", 
                    response_model=SessionResponse, 
                    summary="Start Interview Session",
                    description="Start a new interview session using a valid access token")
def start_session(
    session_data: SessionStart,
    db: Session = db_dependency
):
    """
    Start a new interview session using a valid token.
    
    The token is marked as used, and a new session is created for the candidate.
    Each token can only be used to start one session.
    
    Parameters:
    - **session_data**: Contains the token to use for starting the session
    
    Returns:
    - Session details including ID and start time
    
    Raises:
    - HTTP 400: If token is invalid or already used
    """
    # Verify token
    token = db.query(Token).filter(
        Token.token_value == session_data.token,
        Token.is_used == False
    ).first()
    
    if not token:
        bad_request("Invalid or used token")
    
    # Mark token as used
    token.is_used = True
    
    # Create session
    session = CandidateSession(token_id=token.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session

@sessions_router.post("/session/{session_id}/complete",
                    summary="Complete Interview Session",
                    description="Mark an interview session as completed",
                    response_model=Dict[str, str])
def complete_session(
    session_id: int,
    db: Session = db_dependency
):
    """
    Mark a session as completed by setting the end time.
    
    This should be called when a candidate finishes their interview session.
    Once marked as complete, the session's recordings become available in the results.
    
    Parameters:
    - **session_id**: ID of the session to complete
    
    Returns:
    - Success message
    
    Raises:
    - HTTP 404: If session not found
    """
    session = db.query(CandidateSession).filter(CandidateSession.id == session_id).first()
    
    if not session:
        not_found("Session", session_id)
    
    session.end_time = datetime.utcnow()
    db.commit()
    
    return {"message": "Session completed successfully"}