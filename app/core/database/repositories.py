"""
Repository classes for database operations.

This module implements the repository pattern, separating database    @staticmethod
    def get_by_id(db: Session, interview_id: int, interviewer_id: Optional[int] = None) -> Optional[Interview]:
        'Get an interview by ID, optionally checking interviewer'
        query = db.query(Interview).filter(Interview.id == interview_id)
        if interviewer_id:
            query = query.filter(Interview.interviewer_id == interviewer_id)
        return query.first() logic
from business logic. This improves maintainability, testability and separation
of concerns.
"""
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone

from app.core.database.models import User, PendingAccount, Interview, Question, Token, CandidateSession, Recording


class UserRepository:
    """
    Repository for User-related database operations.
    Centralizes all user queries to improve maintainability.
    """
    
    @staticmethod
    def get_by_id(db: Session, user_id: str) -> Optional[User]:
        """Get a user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        """Get a user by username"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Get a user by email"""
        return db.query(User).filter(User.email == email).first()
        
    @staticmethod
    def get_by_payment_method_id(db: Session, payment_method_id: str) -> Optional[User]:
        """Get a user by payment method ID"""
        return db.query(User).filter(User.payment_method_id == payment_method_id).first()

    @staticmethod
    def create_user(db: Session, user_data: Dict[str, Any]) -> User:
        """Create a new user"""
        user = User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def update_subscription(
        db: Session, 
        user: User, 
        subscription_id: str,
        customer_id: str,
        plan_id: str,
        status: str,
        end_date: datetime
    ) -> User:
        """Update a user's subscription details"""
        user.subscription_id = subscription_id
        user.payment_method_id = customer_id
        user.subscription_plan = plan_id
        user.subscription_status = status
        user.subscription_end_date = end_date
        user.is_active = status == "active"
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def mark_subscription_inactive(db: Session, user: User, status: str = "expired") -> User:
        """Mark a user's subscription as inactive"""
        user.is_active = False
        user.subscription_status = status
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def mark_subscription_active(db: Session, user: User) -> User:
        """Mark a user's subscription as active"""
        user.is_active = True
        user.subscription_status = "active"
        db.commit()
        db.refresh(user)
        return user


class PendingAccountRepository:
    """Repository for pending account operations"""
    
    @staticmethod
    def get_by_token(db: Session, token: str) -> Optional[PendingAccount]:
        """Get a pending account by verification token"""
        return db.query(PendingAccount).filter(
            PendingAccount.verification_token == token,
            PendingAccount.expiration_date > datetime.now(timezone.utc)
        ).first()
    
    @staticmethod
    def create(db: Session, account_data: Dict[str, Any]) -> PendingAccount:
        """Create a new pending account"""
        account = PendingAccount(**account_data)
        db.add(account)
        db.commit()
        db.refresh(account)
        return account
    
    @staticmethod
    def delete(db: Session, account: PendingAccount) -> None:
        """Delete a pending account"""
        db.delete(account)
        db.commit()


class InterviewRepository:
    """Repository for interview operations"""
    
    @staticmethod
    def get_by_id(db: Session, interview_id: int, interviewer_id: Optional[int] = None) -> Optional[Interview]:
        """Get an interview by ID, optionally checking interviewer"""        
        query = db.query(Interview).filter(Interview.id == interview_id)
        if interviewer_id:
            query = query.filter(Interview.interviewer_id == interviewer_id)
        return query.first()
    
    @staticmethod
    def get_by_slug(db: Session, slug: str, interviewer_id: Optional[int] = None) -> Optional[Interview]:
        """Get an interview by slug, optionally checking interviewer"""
        query = db.query(Interview).filter(Interview.slug == slug)
        if interviewer_id:
            query = query.filter(Interview.interviewer_id == interviewer_id)
        return query.first()
    
    @staticmethod
    def get_all_by_interviewer(db: Session, interviewer_id: int) -> List[Interview]:
        """Get all interviews owned by an interviewer"""
        return db.query(Interview).filter(Interview.interviewer_id == interviewer_id).all()
    
    @staticmethod
    def create(db: Session, interview_data: Dict[str, Any]) -> Interview:
        """Create a new interview"""
        # Generate slug if not provided
        if "slug" not in interview_data and "title" in interview_data:
            from app.utils.slug_utils import generate_slug_from_title
            interview_data["slug"] = generate_slug_from_title(interview_data["title"])
            
        interview = Interview(**interview_data)
        db.add(interview)
        db.commit()
        db.refresh(interview)
        return interview
    
    @staticmethod
    def update(db: Session, interview: Interview, update_data: Dict[str, Any]) -> Interview:
        """Update an interview"""
        # If title is updated but slug isn't, regenerate the slug
        if "title" in update_data and "slug" not in update_data:
            from app.utils.slug_utils import generate_slug_from_title
            # Use the last part of the existing slug as suffix for consistency
            if interview.slug:
                suffix = interview.slug.split('-')[-1]
                update_data["slug"] = generate_slug_from_title(update_data["title"], suffix)
            else:
                update_data["slug"] = generate_slug_from_title(update_data["title"])
                
        for key, value in update_data.items():
            setattr(interview, key, value)
        db.commit()
        db.refresh(interview)
        return interview
    
    @staticmethod
    def delete(db: Session, interview: Interview) -> None:
        """Delete an interview"""
        db.delete(interview)
        db.commit()


class TokenRepository:
    """Repository for token operations"""
    
    @staticmethod
    def get_by_value(db: Session, token_value: str) -> Optional[Token]:
        """Get a token by its value"""
        return db.query(Token).filter(Token.token_value == token_value).first()
    
    @staticmethod
    def get_all_by_interview(db: Session, interview_id: int) -> List[Token]:
        """Get all tokens for an interview"""
        return db.query(Token).filter(Token.interview_id == interview_id).all()
    
    @staticmethod
    def create(db: Session, token_data: Dict[str, Any]) -> Token:
        """Create a new token"""
        token = Token(**token_data)
        db.add(token)
        db.commit()
        db.refresh(token)
        return token
    
    @staticmethod
    def mark_used(db: Session, token: Token) -> Token:
        """Mark a token as used"""
        token.is_used = True
        db.commit()
        db.refresh(token)
        return token
    
    @staticmethod
    def delete(db: Session, token: Token) -> None:
        """Delete a token"""
        db.delete(token)
        db.commit()


class SessionRepository:
    """Repository for candidate session operations"""
    
    @staticmethod
    def get_by_id(db: Session, session_id: int) -> Optional[CandidateSession]:
        """Get a session by ID"""
        return db.query(CandidateSession).filter(CandidateSession.id == session_id).first()
    
    @staticmethod
    def get_by_token(db: Session, token_id: int) -> Optional[CandidateSession]:
        """Get a session by token ID"""
        return db.query(CandidateSession).filter(CandidateSession.token_id == token_id).first()
    
    @staticmethod
    def create(db: Session, session_data: Dict[str, Any]) -> CandidateSession:
        """Create a new session"""
        session = CandidateSession(**session_data)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    
    @staticmethod
    def delete(db: Session, session: CandidateSession) -> None:
        """Delete a session and its recordings"""
        # Delete associated recordings
        db.query(Recording).filter(Recording.session_id == session.id).delete()
        # Delete the session
        db.delete(session)
        db.commit()


class RecordingRepository:
    """Repository for recording operations"""
    
    @staticmethod
    def get_by_id(db: Session, recording_id: int) -> Optional[Recording]:
        """Get a recording by ID"""
        return db.query(Recording).filter(Recording.id == recording_id).first()
    
    @staticmethod
    def get_by_session_and_question(
        db: Session, 
        session_id: int, 
        question_id: int
    ) -> Optional[Recording]:
        """Get a recording by session ID and question ID"""
        return db.query(Recording).filter(
            Recording.session_id == session_id,
            Recording.question_id == question_id
        ).first()
    
    @staticmethod
    def get_all_by_session(db: Session, session_id: int) -> List[Recording]:
        """Get all recordings for a session"""
        return db.query(Recording).filter(Recording.session_id == session_id).all()
    
    @staticmethod
    def create(db: Session, recording_data: Dict[str, Any]) -> Recording:
        """Create a new recording"""
        recording = Recording(**recording_data)
        db.add(recording)
        db.commit()
        db.refresh(recording)
        return recording
    
    @staticmethod
    def update(db: Session, recording: Recording, update_data: Dict[str, Any]) -> Recording:
        """Update a recording"""
        for key, value in update_data.items():
            setattr(recording, key, value)
        db.commit()
        db.refresh(recording)
        return recording
    
    @staticmethod
    def delete(db: Session, recording: Recording) -> None:
        """Delete a recording"""
        db.delete(recording)
        db.commit()