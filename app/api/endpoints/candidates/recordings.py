"""
Endpoints for candidate recording management.
Handles uploading and storing audio recordings.
All processing logic has been moved to the service layer.
"""
from fastapi import APIRouter, File, UploadFile, Form
from sqlalchemy.orm import Session
import os

from app.api.dependencies import db_dependency
from app.api.dependencies import recording_service_dependency
from app.schemas import RecordingResponse
from app.services.recordings.recording_service import RecordingService

# Create router
recordings_router = APIRouter()

@recordings_router.post("", 
                     response_model=RecordingResponse,
                     summary="Save Question Recording",
                     description="Upload and save an audio recording answer for a specific question")
async def save_recording(
    token: str = Form(..., description="Token used to start the session"),
    question_id: int = Form(...),
    audio_file: UploadFile = File(...),
    db: Session = db_dependency,
    recording_service: RecordingService = recording_service_dependency
):
    """
    Save a recording for a specific question in a session.
    
    This endpoint handles:
    1. Audio file upload and storage (S3 in production)
    2. Recording metadata storage in database
    
    Note: Transcription and analysis are now handled via batch processing 
    after session completion or through the /batch/analyze endpoint.
    
    Parameters:
    - **token**: Token used to start the session
    - **question_id**: ID of the question being answered
    - **audio_file**: The audio recording file
    
    Returns:
    - Recording details including ID and file path. Transcript and analysis will be added later via batch processing.
    
    Raises:
    - HTTP 404: If session or question not found
    - HTTP 400: If file validation fails    """
    # Read file content before passing to service
    file_content = await audio_file.read()
    file_extension = os.path.splitext(audio_file.filename)[1]
    
    # Delegate business logic to the service (upload-only, no transcription)
    recording = await recording_service.save_recording_by_token(
        token=token,
        question_id=question_id,
        file_content=file_content,
        file_extension=file_extension,
        db=db
    )
    
    return recording
