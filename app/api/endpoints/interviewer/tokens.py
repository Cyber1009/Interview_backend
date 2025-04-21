"""
Endpoints for managing interview access tokens.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.api.deps import db_dependency, active_user_dependency
from app.core.database.models import User, Interview, Token
from app.schemas import CandidateTokenResponse
from app.utils.error_utils import not_found, bad_request

# Create router
tokens_router = APIRouter()

@tokens_router.post("/{interview_id}/tokens", response_model=CandidateTokenResponse)
def generate_token(
    interview_id: int,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Generate a token for a candidate"""
    # Verify interview exists and belongs to user
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.owner_id == current_user.id
    ).first()
    
    if not interview:
        not_found("Interview", interview_id)
    
    # Create token
    token = Token(
        token_value=str(uuid.uuid4()),
        interview_id=interview_id,
        is_used=False
    )
    
    db.add(token)
    db.commit()
    db.refresh(token)
    
    return token

@tokens_router.post("/{interview_id}/tokens/bulk", response_model=List[CandidateTokenResponse])
def generate_bulk_tokens(
    interview_id: int,
    count: int = 10,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Generate multiple tokens for candidates"""
    # Verify interview exists and belongs to user
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.owner_id == current_user.id
    ).first()
    
    if not interview:
        not_found("Interview", interview_id)
    
    # Limit bulk generation to reasonable amounts
    if count > 100:
        count = 100
    
    # Create tokens
    tokens = []
    for _ in range(count):
        token = Token(
            token_value=str(uuid.uuid4()),
            interview_id=interview_id,
            is_used=False
        )
        db.add(token)
        tokens.append(token)
    
    db.commit()
    
    # Refresh all tokens
    for token in tokens:
        db.refresh(token)
    
    return tokens

@tokens_router.get("/{interview_id}/tokens", response_model=List[CandidateTokenResponse])
def get_tokens(
    interview_id: int,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Get all tokens for a specific interview"""
    # Verify interview exists and belongs to user
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.owner_id == current_user.id
    ).first()
    
    if not interview:
        not_found("Interview", interview_id)
    
    # Get tokens
    tokens = db.query(Token).filter(Token.interview_id == interview_id).all()
    return tokens

@tokens_router.delete("/{interview_id}/tokens/{token_value}", status_code=status.HTTP_204_NO_CONTENT)
def delete_token(
    interview_id: int,
    token_value: str,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """Delete a specific token"""
    # Verify interview exists and belongs to user
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.owner_id == current_user.id
    ).first()
    
    if not interview:
        not_found("Interview", interview_id)
    
    # Get the token
    token = db.query(Token).filter(
        Token.token_value == token_value,
        Token.interview_id == interview_id
    ).first()
    
    if not token:
        not_found("Token", token_value)
    
    # Delete token
    db.delete(token)
    db.commit()
    
    return None