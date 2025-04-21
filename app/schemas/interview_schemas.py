"""
Interview, questions, and session related schemas.
"""
from pydantic import BaseModel
from typing import List, Optional, ForwardRef
from datetime import datetime

# Forward reference to avoid circular imports
RecordingResponse = ForwardRef("RecordingResponse")

# Interview Schemas
class QuestionBase(BaseModel):
    text: str
    preparation_time: float = 30.0
    responding_time: float = 60.0

class QuestionCreate(QuestionBase):
    pass

class QuestionResponse(QuestionBase):
    id: int
    order: int
    
    class Config:
        from_attributes = True  # Updated from orm_mode = True

class QuestionOrderUpdate(BaseModel):
    question_id: int
    new_order: int

class InterviewBase(BaseModel):
    title: str

class InterviewCreate(InterviewBase):
    pass

class InterviewResponse(InterviewBase):
    id: int
    questions: List[QuestionResponse]
    created_at: datetime
    
    class Config:
        from_attributes = True  # Updated from orm_mode = True

# Token Schemas
class CandidateTokenCreate(BaseModel):
    interview_id: int

class CandidateTokenResponse(BaseModel):
    token_value: str
    
    class Config:
        from_attributes = True  # Updated from orm_mode = True

class TokenVerify(BaseModel):
    token: str

class TokenVerifyResponse(BaseModel):
    valid: bool
    interview_id: Optional[int] = None
    
    class Config:
        from_attributes = True  # Updated from orm_mode = True

# Candidate Session Schemas
class SessionStart(BaseModel):
    token: str

class SessionResponse(BaseModel):
    id: int
    start_time: datetime
    
    class Config:
        from_attributes = True  # Updated from orm_mode = True

# Results Schema
class InterviewResult(BaseModel):
    session_id: int
    token_value: str
    start_time: datetime
    end_time: Optional[datetime]
    recordings: List[RecordingResponse]
    
    class Config:
        from_attributes = True  # Updated from orm_mode = True

# Update forward references
from app.schemas.recording_schemas import RecordingResponse
InterviewResult.update_forward_refs()