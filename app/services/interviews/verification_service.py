"""
Verification service for the candidates domain.
Handles business logic related to token verification and interview access.
"""
import logging
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.database.models import Token, Interview

# Configure logging
logger = logging.getLogger(__name__)

class VerificationService:
    """
    Service for handling token verification operations.
    Implements business logic for validating tokens and retrieving interview details.
    """
    
    def verify_token(self, token_value: str, db: Session, check_used: bool = True) -> dict:
        """
        Verify if a candidate token exists and is not expired with enhanced validation.
        
        Args:
            token_value: The token to verify
            db: Database session
            check_used: Whether to check if the token has been used (default: True)
            
        Returns:
            Dict with verification result and interview ID if valid
        """
        # Check if token exists 
        token = db.query(Token).filter(
            Token.token_value == token_value
        ).first()
        
        if not token:
            logger.info(f"Invalid token attempted: {token_value}")
            return {"valid": False, "status": "invalid"}
        
        # Check if token has expired (using the expires_at field if set)
        now = datetime.now(timezone.utc)
        if token.expires_at and token.expires_at < now:
            logger.info(f"Expired token attempted: {token_value}")
            return {"valid": False, "status": "expired", "message": "This token has expired"}
        
        # Fallback: Check if token is expired using old logic (older than 7 days) for backward compatibility
        if not token.expires_at:
            expiration_date = token.created_at + timedelta(days=7)
            if expiration_date < now:
                logger.info(f"Expired token attempted (legacy logic): {token_value}")
                return {"valid": False, "status": "expired", "message": "This token has expired"}
        
        # Check if token has exceeded max attempts
        if token.current_attempts >= token.max_attempts:
            logger.info(f"Token exceeded max attempts: {token_value} ({token.current_attempts}/{token.max_attempts})")
            return {"valid": False, "status": "attempts_exceeded", "message": "Maximum session attempts exceeded for this token"}
        
        # Check if token is already used (if requested) - backward compatibility check
        if check_used and token.is_used:
            logger.info(f"Used token attempted: {token_value}")
            return {"valid": False, "status": "used", "message": "This token has already been used"}
        
        logger.info(f"Token {token_value} verified successfully for interview {token.interview_id}")
        return {"valid": True, "interview_id": token.interview_id, "status": "valid", "token_obj": token}
    
    def get_interview_by_token(self, token_value: str, db: Session) -> Interview:
        """
        Get interview details using a valid token.
        
        Args:
            token_value: The token value
            db: Database session
            
        Returns:
            The Interview object with all its questions
            
        Raises:
            HTTPException: If token or interview not found
        """
        # Get token object
        token = db.query(Token).filter(Token.token_value == token_value).first()
        
        if not token:
            logger.warning(f"Token not found: {token_value}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Token not found"
            )
        
        # Get interview
        interview = db.query(Interview).filter(Interview.id == token.interview_id).first()
        
        if not interview:
            logger.error(f"Interview {token.interview_id} not found for token {token_value}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview not found"
            )
        
        logger.info(f"Interview {interview.id} retrieved successfully using token {token_value}")
        return interview
    
    def get_interview_by_slug(self, slug: str, db: Session) -> Interview:
        """
        Get interview details using a slug.
        
        Args:
            slug: The interview slug
            db: Database session
            
        Returns:
            The Interview object with all its questions
            
        Raises:
            HTTPException: If interview not found
        """
        # Get interview by slug
        interview = db.query(Interview).filter(Interview.slug == slug).first()
        
        if not interview:
            logger.warning(f"Interview with slug '{slug}' not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview not found"
            )
        
        logger.info(f"Interview {interview.id} retrieved successfully using slug {slug}")
        return interview
    
    def get_interview_by_id(self, interview_id: int, db: Session) -> Interview:
        """
        Get interview details using an ID.
        
        Args:
            interview_id: The interview ID
            db: Database session
            
        Returns:
            The Interview object with all its questions
            
        Raises:
            HTTPException: If interview not found
        """
        # Get interview by ID
        interview = db.query(Interview).filter(Interview.id == interview_id).first()
        
        if not interview:
            logger.warning(f"Interview with ID {interview_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview not found"
            )
        
        logger.info(f"Interview {interview.id} retrieved successfully using ID")
        return interview
