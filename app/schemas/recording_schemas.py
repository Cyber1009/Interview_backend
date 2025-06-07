"""
Recording, transcription and analysis related schemas.
"""
from pydantic import BaseModel, field_validator, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from app.schemas.base_schemas import EntityBase
from app.schemas.common_schemas import RecordingResponseBase, AnalysisResultBase

# --- Base schemas ---

class RecordingBase(BaseModel):
    """Base schema for recording information"""
    session_id: int
    file_path: Optional[str] = None


class RecordingIdentifierBase(BaseModel):
    """Base schema for recording identifiers"""
    session_id: int
    question_id: int


# Reuse the common AnalysisBase to avoid duplication
AnalysisBase = AnalysisResultBase


# --- Recording Schemas ---

class RecordingCreate(RecordingIdentifierBase):
    """Schema for creating a new recording"""
    audio_data: str = Field(..., description="Base64 encoded audio data")


class RecordingResponse(RecordingResponseBase):
    """Schema for recording response with transcription and analysis status"""
    # The base is already defined in common_schemas
    file_path: str  # Override with required field
    transcript: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    
    @field_validator('analysis', mode='before')
    @classmethod
    def parse_analysis(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return None
        return v


class RecordingWithTranscription(RecordingBase, EntityBase):
    """Schema for recording with simplified transcription details"""
    duration: Optional[int] = None
    created_at: datetime
    transcription: Optional[str] = None


# --- Transcription Schemas ---

class TranscriptionRequest(BaseModel):
    """Schema for transcription service request parameters"""
    model: str = Field(default="whisper-1", description="AI model to use for transcription")
    language: Optional[str] = Field(default=None, description="Language code if known")
    prompt: Optional[str] = Field(default=None, description="Optional prompt to guide transcription")
    temperature: Optional[float] = Field(default=0.0, description="Model temperature parameter")


class TranscriptionResponse(BaseModel):
    """Schema for transcription service response"""
    text: str
    duration: Optional[float] = None
    language: Optional[str] = None
    model_used: str


# --- Analysis Schemas ---

class KeywordExtractionResponse(BaseModel):
    """Schema for keyword extraction from transcription"""
    keywords: List[str]


class SentimentAnalysisResponse(BaseModel):
    """Schema for sentiment analysis of transcription"""
    sentiment: str
    confidence: float
    emotions: Optional[List[str]] = None
    explanation: Optional[str] = None


class InterviewAnalysisQuestionResponse(BaseModel):
    """Schema for analysis of a single question response"""
    question: str
    response_quality: str
    comments: str


class InterviewAnalysisResponse(AnalysisBase):
    """Schema for basic interview analysis"""
    question_responses: Optional[List[InterviewAnalysisQuestionResponse]] = None


class AnalysisScores(BaseModel):
    """Schema for the scoring components of an interview analysis"""
    relevance: float
    technical_accuracy: float
    communication: float
    understanding: float
    practical_application: float
    overall_score: float


class EnhancedInterviewAnalysisResponse(AnalysisBase):
    """Enhanced schema for interview analysis with detailed scoring"""
    scores: AnalysisScores
    response_quality: str
    improvement_suggestions: Optional[List[str]] = None


class RecordingDetails(BaseModel):
    """Schema for detailed session recording information used in results endpoints"""
    session_id: int
    candidate_name: Optional[str] = None
    recordings: List[RecordingResponse]
    start_time: datetime
    end_time: Optional[datetime] = None
    total_questions: int
    completed_questions: int
    
    class Config:
        from_attributes = True
