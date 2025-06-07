"""
Database ORM models for the Interview Backend application.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database.db import Base
import uuid
from datetime import datetime, timedelta

# Import theme defaults from dedicated theme schema
from app.schemas.theme_schemas import (
    DEFAULT_PRIMARY_COLOR,
    DEFAULT_ACCENT_COLOR,
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_TEXT_COLOR
)

def create_tables(engine):
    Base.metadata.create_all(bind=engine)

class PendingAccount(Base):
    __tablename__ = "pending_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    email = Column(String, unique=True, index=True, nullable=True)
    company = Column(String, nullable=True)  # Changed from company_name
    verification_token = Column(String, unique=True, index=True)
    expiration_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set expiration date to one week from creation
        if not self.expiration_date:
            self.expiration_date = datetime.now() + timedelta(days=7)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    email = Column(String, unique=True, index=True, nullable=True)
    company = Column(String, nullable=True)  
    
    # Account access control - independent from subscription state
    # This allows admins to manually suspend accounts regardless of payment status
    is_active = Column(
        Boolean, 
        default=True,
        comment="Administrative override for account access; controls login ability"
    )
    
    # Payment integration fields - these connect to external payment processor
    subscription_id = Column(
        String, 
        nullable=True,
        comment="External reference ID from payment provider; persists across renewals of same plan"
    )
    payment_method_id = Column(
        String, 
        nullable=True,
        comment="Reference to saved payment method in payment processor (e.g., credit card)"
    )
    
    # Subscription details
    subscription_plan = Column(
        String, 
        nullable=True,
        comment="Plan tier determining feature access (basic, premium, etc.)"
    )
    subscription_end_date = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Date when current billing period ends; used to determine expiration"
    )
    subscription_status = Column(
        String, 
        default="inactive",
        comment="Detailed subscription state: active, expired, trial, canceled, etc."
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
      # Relationships
    interviews = relationship("Interview", back_populates="interviewer")
    theme = relationship("UserTheme", uselist=False, back_populates="user")
    
    @property
    def has_active_subscription(self):
        """Check if user has a valid subscription that grants feature access"""
        if not self.subscription_plan or not self.subscription_end_date:
            return False
            
        return (self.subscription_status == "active" and 
                self.subscription_end_date > datetime.now())
    
    @property
    def can_login(self):
        """Check if user is allowed to log into the system"""
        return self.is_active

class Admin(Base):
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    email = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    # Commenting out timestamp fields as they're not essential for troubleshooting
    # created_at = Column(DateTime(timezone=True), server_default=func.now())
    # last_login = Column(DateTime(timezone=True), nullable=True)

class UserTheme(Base):
    __tablename__ = "user_themes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Updated logo storage - S3 support with development fallback
    company_logo_url = Column(String, nullable=True)  # S3 URL or local file path
    company_logo_s3_key = Column(String, nullable=True)  # S3 key for management
    storage_type = Column(String, default="local")  # "local" or "s3"
    
    # Keep old column for migration compatibility (will be removed later)
    company_logo = Column(String, nullable=True)  # Deprecated: data URL storage
    
    primary_color = Column(String, default=DEFAULT_PRIMARY_COLOR)  # Default from schema constants
    accent_color = Column(String, default=DEFAULT_ACCENT_COLOR)  # Default from schema constants
    background_color = Column(String, default=DEFAULT_BACKGROUND_COLOR)  # Default from schema constants
    text_color = Column(String, default=DEFAULT_TEXT_COLOR)  # Default from schema constants
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="theme")

class Interview(Base):
    __tablename__ = "interviews"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    slug = Column(String, unique=True, index=True, nullable=True)
    interviewer_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    interviewer = relationship("User", back_populates="interviews")
    questions = relationship("Question", back_populates="interview", order_by="Question.order")
    tokens = relationship("Token", back_populates="interview")

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), index=True)
    text = Column(Text)
    order = Column(Integer)
    preparation_time = Column(Float, default=30.0)  # Time in seconds
    responding_time = Column(Float, default=60.0)  # Time in seconds
    
    # Relationships
    interview = relationship("Interview", back_populates="questions")
    recordings = relationship("Recording", back_populates="question")  # Added missing relationship

class Token(Base):
    __tablename__ = "tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token_value = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    interview_id = Column(Integer, ForeignKey("interviews.id"))
    candidate_name = Column(String, nullable=True)  # Name of the candidate this token is for
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Token expiration time
    max_attempts = Column(Integer, default=1)  # Maximum number of session attempts allowed
    current_attempts = Column(Integer, default=0)  # Number of attempts made so far
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    interview = relationship("Interview", back_populates="tokens")
    candidate_sessions = relationship("CandidateSession", back_populates="token")

class CandidateSession(Base):
    __tablename__ = "candidate_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, ForeignKey("tokens.id"))
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    token = relationship("Token", back_populates="candidate_sessions")
    recordings = relationship("Recording", back_populates="session")

class Recording(Base):
    __tablename__ = "recordings"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("candidate_sessions.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    file_path = Column(String)  # Local path or S3 key
    file_url = Column(String, nullable=True)  # Full URL for file access (for S3 presigned URLs)
    storage_type = Column(String, default="local")  # "local" or "s3"
    transcript = Column(Text, nullable=True)
    transcription_status = Column(String, default="pending")  # pending, completed, failed, retry_scheduled
    transcription_error = Column(String, nullable=True)
    transcription_retry_count = Column(Integer, default=0)  # Track number of retry attempts
    next_retry_at = Column(DateTime(timezone=True), nullable=True)  # Schedule for next retry
    analysis = Column(Text, nullable=True)  # JSON-encoded analysis results
    analysis_status = Column(String, default="pending")  # pending, completed, failed
    analysis_error = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("CandidateSession", back_populates="recordings")
    question = relationship("Question", back_populates="recordings")