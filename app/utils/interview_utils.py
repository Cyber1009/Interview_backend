"""
Utility functions for interview-related operations.
"""
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database.models import Interview, User
from app.core.database.repositories import InterviewRepository
from app.api.exceptions import not_found


def get_interview_by_key(
    db: Session, 
    interview_key: str, 
    user_id: int, 
    raise_if_not_found: bool = True
) -> Optional[Interview]:
    """
    Get an interview by key (ID or slug) with ownership verification.
    
    Args:
        db: Database session
        interview_key: Either a numeric ID or a URL-friendly slug
        user_id: The ID of the user who should own the interview
        raise_if_not_found: Whether to raise an exception if not found
        
    Returns:
        Interview object if found, None if not found and raise_if_not_found=False
        
    Raises:
        HTTPException: If interview not found and raise_if_not_found=True
    """
    # Check if the parameter is a numeric ID or a slug
    is_numeric = interview_key.isdigit()
    
    if is_numeric:
        interview = InterviewRepository.get_by_id(db, int(interview_key), user_id)
    else:
        interview = InterviewRepository.get_by_slug(db, interview_key, user_id)
    
    if not interview and raise_if_not_found:
        not_found("Interview", interview_key)
    
    return interview
