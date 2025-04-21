"""
Endpoints for candidate token verification.
Handles verifying access tokens and retrieving interview details.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_dependency
from app.core.database.models import Token, Interview
from app.schemas.interview_schemas import TokenVerify, TokenVerifyResponse, InterviewResponse
from app.utils.error_utils import not_found

# Create router
verification_router = APIRouter()

@verification_router.post("/verify-token", 
                        response_model=TokenVerifyResponse,
                        summary="Verify Interview Token",
                        description="Verify if a candidate token is valid and has not been used")
def verify_token(
    token_data: TokenVerify,
    db: Session = db_dependency
):
    """
    Verify if a candidate token is valid and not already used.
    
    This is the first step in the candidate interview flow:
    1. Candidate enters their access token
    2. System verifies the token is valid
    3. If valid, candidate proceeds to start session
    
    Parameters:
    - **token_data**: Contains the token string to verify
    
    Returns:
    - **valid**: Boolean indicating if token is valid
    - **interview_id**: ID of associated interview if token is valid
    """
    token = db.query(Token).filter(
        Token.token_value == token_data.token,
        Token.is_used == False
    ).first()
    
    if not token:
        return {"valid": False}
    
    return {"valid": True, "interview_id": token.interview_id}

@verification_router.get("/interview/{token}", 
                      response_model=InterviewResponse,
                      summary="Get Interview Details",
                      description="Get interview details and questions using a valid token")
def get_interview_by_token(
    token: str,
    db: Session = db_dependency
):
    """
    Get interview details and questions using a valid token.
    
    This endpoint allows candidates to retrieve all interview details including:
    - Interview title
    - All questions with their text and timing parameters
    
    Parameters:
    - **token**: The access token string
    
    Returns:
    - Complete interview details including all questions
    
    Raises:
    - HTTP 404: If token or interview not found
    """
    # Get token object
    token_obj = db.query(Token).filter(Token.token_value == token).first()
    
    if not token_obj:
        not_found("Token", token)
    
    # Get interview
    interview = db.query(Interview).filter(Interview.id == token_obj.interview_id).first()
    
    if not interview:
        not_found("Interview", token_obj.interview_id)
    
    return interview