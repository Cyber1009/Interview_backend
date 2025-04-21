"""
Database ORM models for the Interview Backend application.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database.db import Base
import uuid
from datetime import datetime, timedelta

def create_tables(engine):
    Base.metadata.create_all(bind=engine)

class PendingAccount(Base):
    __tablename__ = "pending_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    email = Column(String, unique=True, index=True, nullable=True)
    company_name = Column(String, nullable=True)
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
    company_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)  # For account suspension
    subscription_id = Column(String, nullable=True)  # External subscription ID
    subscription_plan = Column(String, nullable=True)  # Plan name (basic, premium, etc.)
    subscription_end_date = Column(DateTime(timezone=True), nullable=True)
    subscription_status = Column(String, default="inactive")  # active, inactive, trial, etc.
    payment_method_id = Column(String, nullable=True)  # ID from payment processor
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    interviews = relationship("Interview", back_populates="owner")
    theme = relationship("UserTheme", uselist=False, back_populates="user")

class UserTheme(Base):
    __tablename__ = "user_themes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    company_logo = Column(String, nullable=True)  # URL or path to logo image
    primary_color = Column(String, default="#3498db")  # Default blue
    secondary_color = Column(String, default="#2ecc71")  # Default green
    accent_color = Column(String, default="#e74c3c")  # Default red
    background_color = Column(String, default="#f5f5f5")  # Default light gray
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="theme")

class Interview(Base):
    __tablename__ = "interviews"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="interviews")
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

class Token(Base):
    __tablename__ = "tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token_value = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    interview_id = Column(Integer, ForeignKey("interviews.id"))
    is_used = Column(Boolean, default=False)
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
    file_path = Column(String)
    transcript = Column(Text, nullable=True)
    transcription_status = Column(String, default="pending")  # pending, completed, failed
    transcription_error = Column(String, nullable=True)
    analysis = Column(Text, nullable=True)  # JSON-encoded analysis results
    analysis_status = Column(String, default="pending")  # pending, completed, failed
    analysis_error = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("CandidateSession", back_populates="recordings")
    question = relationship("Question")