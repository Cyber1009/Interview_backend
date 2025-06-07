"""
Interview, questions, and session related schemas.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.schemas.base_schemas import (
    EntityBase,
    TimestampBase,
    CandidateTokenBase
)

from app.schemas.common_schemas import RecordingResponseBase
from app.schemas.theme_schemas import UserTheme

# --- Custom TimestampBase for Interview Sessions ---

class InterviewTimestampBase(BaseModel):
    """Base schema for interview-specific timestamp information"""
    start_time: datetime
    end_time: Optional[datetime] = None


# --- Question Schemas ---

class QuestionBase(BaseModel):
    """Base schema for interview questions"""
    text: str
    preparation_time: float = Field(default=30.0, description="Time in seconds for preparation")
    responding_time: float = Field(default=60.0, description="Time in seconds for responding")
    
    @field_validator('preparation_time', 'responding_time')
    @classmethod
    def time_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Time must be greater than 0')
        return v


class QuestionListResponse(BaseModel):
    """Schema for question response when listing interviews, allows zero values"""
    id: int
    text: str
    preparation_time: float
    responding_time: float
    order: int
    
    class Config:
        from_attributes = True


class QuestionResponse(QuestionBase, EntityBase):
    """Schema for question response with ID and ordering"""
    order: int
    
    class Config:
        from_attributes = True


class QuestionOrderUpdate(BaseModel):
    """Schema for updating the order of questions"""
    question_id: int = Field(..., description="ID of the question to reorder")
    new_order: int = Field(..., description="New position for the question (1-based)")    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "question_id": 42,
                "new_order": 2
            }
        }


class QuestionUpdateOrCreate(QuestionBase):
    """Schema for updating or creating a question in bulk operations"""
    id: Optional[int] = Field(None, description="ID of the question when updating, None when creating new")
    order: int = Field(..., description="Position of the question in the interview")


# --- Interview Schemas ---

class InterviewBase(BaseModel):
    """Base schema for interview information"""
    title: str


class InterviewCreateWithQuestions(InterviewBase):
    """Schema for creating a new interview with optional questions"""
    questions: Optional[List[QuestionUpdateOrCreate]] = Field(default=None, description="Optional list of questions to add during interview creation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Software Developer Interview",
                "questions": [
                    {
                        "id": None,
                        "text": "Tell me about your experience with Python",
                        "preparation_time": 30.0,
                        "responding_time": 90.0,
                        "order": 1
                    },
                    {
                        "id": None,
                        "text": "Describe a challenging project you worked on",
                        "preparation_time": 45.0,
                        "responding_time": 120.0,
                        "order": 2
                    }
                ]
            }
        }


class InterviewListResponse(InterviewBase, EntityBase):
    """Schema for interview list response with questions, allowing zero values"""
    questions: List[QuestionListResponse]
    created_at: datetime
    slug: Optional[str] = None
    
    class Config:
        from_attributes = True


class InterviewResponse(InterviewBase, EntityBase):
    """Schema for interview response with questions"""
    questions: List[QuestionResponse]
    created_at: datetime
    slug: Optional[str] = None
    
    class Config:
        from_attributes = True


class InterviewUpdateWithQuestions(InterviewBase):
    """Schema for complete interview update with questions"""
    questions: List[QuestionUpdateOrCreate]    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated Interview Title",
                "questions": [
                    {
                        "id": 1,
                        "text": "Tell me about your experience with Python",
                        "preparation_time": 30.0,
                        "responding_time": 90.0,
                        "order": 1
                    },
                    {
                        "text": "Describe a challenging project you worked on",
                        "preparation_time": 45.0,
                        "responding_time": 120.0,
                        "order": 2
                    }
                ]
            }
        }


# --- Token Schemas ---

class CandidateTokenCreate(BaseModel):
    """Schema for creating a candidate token with enhanced fields"""
    interview_id: int
    candidate_name: Optional[str] = Field(None, description="Name of the candidate this token is for")
    expires_in_hours: Optional[int] = Field(72, description="Token expiry time in hours (default 72 hours)")
    max_attempts: Optional[int] = Field(1, description="Maximum number of session attempts allowed (default 1)")


class CandidateTokenResponse(BaseModel):
    """Schema for token response with enhanced information"""
    token_value: str
    candidate_name: Optional[str] = None
    is_used: bool = False
    expires_at: Optional[datetime] = None
    max_attempts: int = 1
    current_attempts: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenVerifyResponse(BaseModel):
    """Schema for token verification response"""
    valid: bool
    interview_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class ThemeInfo(BaseModel):
    """Schema for theme information in token verification response"""
    company_logo: Optional[str] = None
    primary_color: str 
    accent_color: str
    background_color: str
    text_color: str    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {                "company_logo": "https://example.com/logo.png",
                "primary_color": "#091326",
                "accent_color": "#52606d",
                "background_color": "#f5f7fa",
                "text_color": "#222222"
            }
        }

class EnhancedInterviewResponse(InterviewResponse):
    """
    Enhanced schema for token-based interview access response with complete interview details and branding.
    
    Used as the response model for the `/interviews/access` endpoint where candidates provide their token
    to access the full interview details including questions and company theme information.
    """    
    theme: Optional[ThemeInfo] = None
    valid: bool = True
    status: str = "valid"
    session_id: Optional[int] = None
    session_created: Optional[bool] = None
    
    class Config:
        from_attributes = True
        
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "Software Developer Interview",
                "interviewer_id": 42,
                "created_at": "2025-05-07T12:00:00Z",
                "questions": [
                    {
                        "id": 1,
                        "text": "Tell me about your experience with Python",
                        "order": 1,
                        "preparation_time": 30.0,
                        "responding_time": 90.0
                    },
                    {
                        "id": 2,
                        "text": "Describe a challenging project you worked on",
                        "order": 2,
                        "preparation_time": 45.0,
                        "responding_time": 120.0
                    }
                ],
                "theme": {                    "company_logo": "https://example.com/company-logo.png",
                    "primary_color": "#091326",
                    "accent_color": "#52606d",
                    "background_color": "#f5f7fa",
                    "text_color": "#222222"                },
                "session_id": 15,
                "session_created": True
            }
        }


# --- Session Schemas ---

class SessionResponse(EntityBase):
    """Schema for session response
    
    Used as response model for both:
    - POST /interviews/start-session - Starting a new interview session 
    - PATCH /interviews/complete-session - Completing an interview session
    """
    start_time: datetime
    
    class Config:
        from_attributes = True


# --- Results Schema ---

class InterviewResult(InterviewTimestampBase):
    """Schema for complete interview results"""
    session_id: int
    token_value: str
    recordings: List[RecordingResponseBase]
    
    class Config:
        from_attributes = True


# --- Transcription and Analysis Schemas ---

class QualityAssessment(BaseModel):
    """Schema for transcription quality assessment"""
    quality_score: float
    needs_upgrade: bool
    quality_issues: List[str]
    metrics: Dict[str, Any]

class TranscriptionResponse(BaseModel):
    """Schema for transcription service response"""
    text: str
    language: Optional[str] = None
    segments: Optional[List[Dict[str, Any]]] = []
    model_used: str
    quality_assessment: Optional[QualityAssessment] = None
    model_upgrades_performed: Optional[int] = 0
    saved_files: Optional[Dict[str, str]] = None

class ContentAnalysis(BaseModel):
    """Schema for content analysis results"""
    communication_skills: Dict[str, Any]
    content_quality: Dict[str, Any]
    professional_competencies: Dict[str, Any]
    interview_performance: Dict[str, Any]
    areas_for_improvement: List[str]
    overall_impression: Dict[str, Any]

class SpeakingAnalysis(BaseModel):
    """Schema for speaking pattern analysis"""
    timing_metrics: Dict[str, Any]
    pause_analysis: Dict[str, Any]
    confidence_indicators: Dict[str, Any]
    behavioral_insights: Dict[str, Any]

class StressAnalysis(BaseModel):
    """Schema for stress detection analysis"""
    stress_level: str
    key_indicators: List[str]
    contextual_factors: List[str]
    recommendations: List[str]

class AuthenticityAnalysis(BaseModel):
    """Schema for authenticity assessment"""
    authenticity_level: str
    key_indicators: List[str]
    concerns: List[str]
    recommendations: List[str]

class OverallAssessment(BaseModel):
    """Schema for overall interview assessment"""
    overall_score: int
    score_breakdown: Dict[str, int]
    key_strengths: List[str]
    areas_of_concern: List[str]
    hiring_recommendation: str
    detailed_rationale: str
    next_steps: List[str]
    interviewer_notes: List[str]

class InterviewAnalysisResponse(BaseModel):
    """Schema for comprehensive interview analysis response"""
    status: str
    timestamp: str
    content_analysis: Optional[ContentAnalysis] = None
    speaking_analysis: Optional[SpeakingAnalysis] = None
    stress_analysis: Optional[StressAnalysis] = None
    authenticity_analysis: Optional[AuthenticityAnalysis] = None
    overall_assessment: Optional[OverallAssessment] = None
    transcript_length: int
    segments_analyzed: int
    transcription_result: Optional[TranscriptionResponse] = None
    saved_files: Optional[Dict[str, str]] = None
    error: Optional[str] = None