"""
Recording, transcription and analysis related schemas.
"""
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

# Recording Schemas
class RecordingCreate(BaseModel):
    session_id: int
    question_id: int
    audio_data: str  # Base64 encoded audio data

class RecordingResponse(BaseModel):
    id: int
    session_id: int
    question_id: int
    file_path: str
    transcript: Optional[str] = None
    transcription_status: str
    analysis: Optional[Dict[str, Any]] = None
    analysis_status: str
    created_at: datetime
    
    @validator('analysis', pre=True)
    def parse_analysis(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return None
        return v
    
    class Config:
        from_attributes = True

class RecordingWithTranscription(BaseModel):
    id: int
    session_id: int
    file_path: str
    duration: Optional[int] = None
    created_at: datetime
    transcription: Optional[str] = None

# Transcription and Analysis Schemas
class TranscriptionRequest(BaseModel):
    model: str = "whisper-1"
    language: Optional[str] = None
    prompt: Optional[str] = None
    temperature: Optional[float] = 0.0

class TranscriptionResponse(BaseModel):
    text: str
    duration: Optional[float] = None
    language: Optional[str] = None
    model_used: str

class KeywordExtractionResponse(BaseModel):
    keywords: List[str]

class SentimentAnalysisResponse(BaseModel):
    sentiment: str
    confidence: float
    emotions: Optional[List[str]] = None
    explanation: Optional[str] = None

class InterviewAnalysisQuestionResponse(BaseModel):
    question: str
    response_quality: str
    comments: str

class InterviewAnalysisResponse(BaseModel):
    key_insights: List[str]
    strengths: List[str]
    weaknesses: List[str]
    question_responses: Optional[List[InterviewAnalysisQuestionResponse]] = None
    overall_assessment: str

class AnalysisScores(BaseModel):
    """Schema for the scoring components of an interview analysis"""
    relevance: float
    technical_accuracy: float
    communication: float
    understanding: float
    practical_application: float
    overall_score: float

class EnhancedInterviewAnalysisResponse(BaseModel):
    """Enhanced schema for interview analysis with detailed scoring"""
    key_insights: List[str]
    strengths: List[str]
    weaknesses: List[str]
    scores: AnalysisScores
    response_quality: str
    overall_assessment: str
    improvement_suggestions: Optional[List[str]] = None