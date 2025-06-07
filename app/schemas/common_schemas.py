"""
Common schemas that are shared between multiple domain schemas.
This module helps avoid circular imports by providing shared models.
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Shared Response Types ---

class RecordingResponseBase(BaseModel):
    """Base schema for recording responses to avoid circular imports"""
    session_id: int
    question_id: int
    id: int
    file_path: Optional[str] = None
    transcription_status: Optional[str] = None
    analysis_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AnalysisResultBase(BaseModel):
    """Base schema for analysis results to avoid circular imports"""
    key_insights: List[str]
    strengths: List[str]
    weaknesses: List[str]
    overall_assessment: str