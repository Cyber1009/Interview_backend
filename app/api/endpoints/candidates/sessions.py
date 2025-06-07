"""
Candidate Portal API - Interview Management Endpoints

This module implements the unified API for candidate interactions with consistent /interviews/ prefix:
1. Interview access and details through /interviews/access
2. Session management through /interviews/start-session and /interviews/complete-session  
3. Recording submission through /interviews/recordings

API Design Principles:
- All endpoints use consistent /interviews/ prefix for better organization
- Token-based authentication for all operations
- Standardized error responses and status codes
- RESTful design patterns

Current Endpoints:
- POST /interviews/access - Access interview details without creating session
- POST /interviews/start-session - Start new interview session
- PATCH /interviews/complete-session - Complete interview session
- POST /interviews/recordings - Upload audio recordings

Security Model:
All candidate operations require a valid interview token. The backend determines which 
interview information to provide based on the token, ensuring candidates can only access 
their assigned interviews.

Response Formats:
All responses follow standardized schemas with consistent error handling and status codes.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Path, BackgroundTasks, Form, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Union
import os

# Import from consolidated dependencies module
from app.api.dependencies import (
    db_dependency,
    verification_service_dependency,
    session_service_dependency,
    recording_service_dependency
)
from app.schemas.interview_schemas import (
    CandidateTokenBase, 
    InterviewResponse,
    EnhancedInterviewResponse,
    SessionResponse
)
from app.schemas.recording_schemas import RecordingResponse
from app.core.database.models import Token, CandidateSession, Recording
from app.services.interviews.verification_service import VerificationService
from app.services.interviews.session_service import SessionService
from app.services.recordings.recording_service import RecordingService

# Configure logging
import logging
logger = logging.getLogger(__name__)

# Create unified router
router = APIRouter()

# ======================================================================
# SECTION: Interview Access (Consolidated API)
# ======================================================================

@router.post("/interviews/access", 
           response_model=EnhancedInterviewResponse,
           summary="Access Interview Details",
           description="Retrieve interview details and configuration using a token without creating a session"
)
def access_interview(
    session_data: CandidateTokenBase,
    db: Session = db_dependency,
    verification_service: VerificationService = verification_service_dependency,
    session_service: SessionService = session_service_dependency
):
    """
    Endpoint to access interview details using a token.
    
    This flow:
    1. Verifies the token is valid (without checking if it's been used)
    2. Returns interview details without marking the token as used
    
    Parameters:
    - **session_data**: Object containing the token to verify
    
    Returns:
    - If valid: Complete interview details with questions, theme settings
    
    Raises:
    - HTTP 400: If token is invalid
    - HTTP 410: If token is expired
    - HTTP 500: If there's an error retrieving interview details
    """
    token = session_data.token
    
    # First check if token is valid, but don't check if it's used yet
    # This allows viewing interview details even if the token has been used before
    token_verify_result = verification_service.verify_token(token, db, check_used=False)
    
    # Use dictionary access instead of attribute access
    if not token_verify_result.get("valid", False):
        # Return error response with appropriate status code
        status_value = token_verify_result.get("status", "invalid")
        
        if status_value == "expired":
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={
                    "status": "expired",
                    "message": "This interview token has expired",
                    "valid": False
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "invalid",
                    "message": "Invalid interview token",
                    "valid": False
                }
            )
    
    # If token is valid, get interview details but don't create a session
    try:
        # Get interview data
        interview = verification_service.get_interview_by_token(token, db)
        
        # Check if token is already used (but don't reject for this endpoint)
        is_used = False
        token_obj = db.query(Token).filter(Token.token_value == token).first()
        if token_obj and token_obj.is_used:
            is_used = True
            
        # Get existing session info
        session = None
        try:
            # Just check if a session exists, don't create one
            session = session_service.get_session_by_token(token, db)
        except Exception as session_error:            # If there's an error handling the session, log it but continue
            logger.warning(f"Failed to check session for token {token}: {str(session_error)}")
          # Get theme information from interview interviewer
        theme_data = {}
        if interview.interviewer and hasattr(interview.interviewer, 'theme') and interview.interviewer.theme:
            theme = interview.interviewer.theme
            theme_data = {
                "company_logo": theme.company_logo,
                "primary_color": theme.primary_color,
                "accent_color": theme.accent_color,
                "background_color": theme.background_color,
                "text_color": theme.text_color
            }
        else:
            # Use default theme values if no theme is set for the interviewer
            from app.schemas.theme_schemas import (
                DEFAULT_PRIMARY_COLOR,
                DEFAULT_ACCENT_COLOR,
                DEFAULT_BACKGROUND_COLOR,
                DEFAULT_TEXT_COLOR
            )
            theme_data = {
                "company_logo": None,
                "primary_color": DEFAULT_PRIMARY_COLOR,
                "accent_color": DEFAULT_ACCENT_COLOR,
                "background_color": DEFAULT_BACKGROUND_COLOR,
                "text_color": DEFAULT_TEXT_COLOR
            }

        # Convert SQLAlchemy model to dictionary manually
        interview_dict = {
            "id": interview.id,
            "title": interview.title,
            "slug": interview.slug,
            "interviewer_id": interview.interviewer_id,
            "created_at": interview.created_at,
            "questions": [
                {
                    "id": q.id,
                    "text": q.text,
                    "order": q.order,
                    "preparation_time": q.preparation_time,
                    "responding_time": q.responding_time
                }
                for q in sorted(interview.questions, key=lambda x: x.order)
            ],
            "status": "valid",
            "valid": True,
            "theme": theme_data,
            "token_used": is_used
        }
        
        # Add session information if it exists
        if session:
            interview_dict["session_id"] = session.id
            interview_dict["session_created"] = True
        else:
            interview_dict["session_created"] = False
        
        return interview_dict
    except Exception as e:
        # Handle errors
        logger.error(f"Error accessing interview for token {token}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": f"Error retrieving interview: {str(e)}",
                "valid": False
            }
        )

# Create a separate endpoint for starting a session
@router.post("/interviews/start-session", 
           response_model=SessionResponse,
           summary="Start Interview Session",
           description="Create a new interview session using a valid token and mark the token as used"
)
def create_interview_session(
    session_data: CandidateTokenBase,
    db: Session = db_dependency,
    verification_service: VerificationService = verification_service_dependency,
    session_service: SessionService = session_service_dependency
):
    """
    Start a new interview session using a valid token.
    
    This is the RECOMMENDED ENDPOINT for starting new sessions.
    
    This endpoint:
    1. Verifies the token is valid and not already used
    2. Marks the token as used
    3. Creates and returns a new session
    
    Parameters:
    - **session_data**: Object containing the token to use
    
    Returns:
    - New session details including ID and start time
    
    Raises:
    - HTTP 400: If token is invalid or already used
    - HTTP 410: If token is expired
    """
    token = session_data.token
    # Verify token (including checking if it's already been used)
    token_verify_result = verification_service.verify_token(token, db, check_used=True)
    if not token_verify_result.get("valid", False):
        status_value = token_verify_result.get("status", "invalid")
        
        if status_value == "expired":
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={
                    "status": "expired",
                    "message": "This interview token has expired",
                    "valid": False
                }
            )
        elif status_value == "used":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "used",
                    "message": "This interview token has already been used",
                    "valid": False
                }
            )
        elif status_value == "attempts_exceeded":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": "attempts_exceeded", 
                    "message": "Maximum session attempts exceeded for this token",
                    "valid": False
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "invalid",
                    "message": "Invalid interview token",
                    "valid": False
                }
            )
    
    # Get the token object from the verification result
    token_obj = token_verify_result.get("token_obj")
    if not token_obj:
        # Fallback to getting token object manually if not provided
        from app.core.database.models import Token
        token_obj = db.query(Token).filter(Token.token_value == token).first()
    
    # If token is valid and not used, create a session
    return session_service.start_session(token_obj, db)

# ======================================================================
# SECTION: Interview Session Management  
# ======================================================================

@router.patch("/interviews/complete-session",
            summary="Complete Interview Session",
            description="Mark an interview session as completed and trigger batch processing",
            response_model=Dict[str, str])
def complete_session(
    session_data: CandidateTokenBase,
    background_tasks: BackgroundTasks,
    db: Session = db_dependency,
    session_service: SessionService = session_service_dependency
):
    """
    Mark a session as completed by setting the end time and trigger batch processing.
    
    This endpoint:
    1. Validates that the session has recordings
    2. Marks the session as completed 
    3. Automatically triggers batch transcription and analysis for all session recordings
    4. Processes all video transcripts together in one LLM request for comprehensive analysis
    
    The session is identified by the token used to start it.
    
    Parameters:
    - **session_data**: Contains the token used to identify the session
    
    Returns:
    - Success message
    
    Raises:
    - HTTP 404: If session not found
    - HTTP 400: If session has no recordings
    """
    # First check if the session exists and has recordings
    token = db.query(Token).filter(Token.token_value == session_data.token).first()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )
    
    # Find session associated with the token
    session = db.query(CandidateSession).filter(CandidateSession.token_id == token.id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No session found for this token"
        )
    
    # Check if session has any recordings
    recording_count = db.query(Recording).filter(Recording.session_id == session.id).count()
    if recording_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "no_recordings",
                "message": "Cannot complete session without any recordings. Please record at least one answer before completing the session.",
                "recording_count": recording_count
            }
        )
    
    # Delegate to service layer with background tasks for batch processing
    session_service.complete_session_by_token(session_data.token, db, background_tasks)
    return {
        "message": f"Session completed successfully with {recording_count} recordings. Batch analysis initiated.",
        "recording_count": recording_count
    }

# ======================================================================
# SECTION: Interview Recording Management
# ======================================================================

# Recording endpoints moved to recordings.py
    session_service.complete_session_by_token(session_data.token, db, background_tasks)
    return {"message": "Session completed successfully. Batch analysis initiated."}

# ======================================================================
# SECTION: Interview Recording Management
# ======================================================================

# Recording endpoints moved to recordings.py
