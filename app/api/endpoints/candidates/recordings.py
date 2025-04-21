"""
Endpoints for candidate recording management.
Handles uploading and storing audio recordings and processing transcriptions and analysis.
"""
from fastapi import APIRouter, Depends, File, UploadFile, Form, BackgroundTasks
from sqlalchemy.orm import Session
import os
import uuid
import aiofiles
import json
import logging

from app.api.deps import db_dependency
from app.core.database.models import CandidateSession, Question, Recording
from app.schemas import RecordingResponse
from app.core.config import settings
from app.utils.error_utils import not_found, internal_error

# Using the enhanced processors from the core directory
from app.core.processors.transcription_processor import TranscriptionProcessor
from app.core.processors.analysis_processor import AnalysisProcessor

# Configure logging
logger = logging.getLogger(__name__)

# Create router
recordings_router = APIRouter()

# Initialize processors
transcription_processor = TranscriptionProcessor()
analysis_processor = AnalysisProcessor()

# Helper function for background transcription and analysis processing
async def process_recording(db: Session, recording_id: int, file_path: str):
    """
    Process audio transcription and analysis in the background.
    This function is designed to be run as a background task.
    """
    # Step 1: Get a fresh db session for this background task
    recording = db.query(Recording).filter(Recording.id == recording_id).first()
    if not recording:
        logger.error(f"Recording not found: ID {recording_id}")
        return
        
    # Get question text for context in analysis - always pass question text for better analysis
    question = db.query(Question).filter(Question.id == recording.question_id).first()
    question_text = question.text if question else None
    
    # Step 2: Transcribe audio
    try:
        transcription_result = transcription_processor.transcribe_file(file_path)
        
        if "error" in transcription_result:
            recording.transcription_status = "failed"
            recording.transcription_error = transcription_result["error"][:500]
            recording.analysis_status = "skipped"  # Skip analysis if transcription failed
            db.commit()
            logger.error(f"Transcription failed for recording {recording_id}: {transcription_result['error']}")
            return
            
        # Update recording with transcription
        recording.transcript = transcription_result["text"]
        recording.transcription_status = "completed"
        db.commit()
        logger.info(f"Transcription completed for recording {recording_id}")
        
    except Exception as e:
        recording.transcription_status = "failed"
        recording.transcription_error = str(e)[:500]
        recording.analysis_status = "skipped"
        db.commit()
        logger.error(f"Error transcribing audio (ID: {recording_id}): {str(e)}")
        return
    
    # Step 3: Analyze the transcript with enhanced scoring and analysis
    try:
        # Always pass the question text for better context-aware analysis
        analysis_result = analysis_processor.analyze_interview(
            transcript=recording.transcript,
            question_text=question_text
        )
        
        if "error" in analysis_result:
            recording.analysis_status = "failed"
            recording.analysis_error = analysis_result["error"][:500]
            db.commit()
            logger.error(f"Analysis failed for recording {recording_id}: {analysis_result['error']}")
            return
            
        # Update recording with enhanced analysis results including scores
        recording.analysis = json.dumps(analysis_result)
        recording.analysis_status = "completed"
        db.commit()
        logger.info(f"Analysis with scoring completed for recording {recording_id}")
        
    except Exception as e:
        recording.analysis_status = "failed"
        recording.analysis_error = str(e)[:500]
        db.commit()
        logger.error(f"Error analyzing transcript (ID: {recording_id}): {str(e)}")

@recordings_router.post("/recordings", 
                      response_model=RecordingResponse,
                      summary="Save Question Recording",
                      description="Upload and save an audio recording answer for a specific question")
async def save_recording(
    background_tasks: BackgroundTasks,
    session_id: int = Form(...),
    question_id: int = Form(...),
    audio_file: UploadFile = File(...),
    db: Session = db_dependency
):
    """
    Save a recording for a specific question in a session.
    
    This endpoint handles:
    1. Audio file upload and storage
    2. Recording metadata storage in database
    3. Asynchronous transcription using OpenAI Whisper as a background task
    4. Asynchronous enhanced analysis with scoring of the transcription
    
    Parameters:
    - **session_id**: ID of the active candidate session
    - **question_id**: ID of the question being answered
    - **audio_file**: The audio recording file
    
    Returns:
    - Recording details including ID and file path. Transcript and analysis will be added later.
    
    Raises:
    - HTTP 404: If session or question not found
    """
    # Verify session exists
    session = db.query(CandidateSession).filter(CandidateSession.id == session_id).first()
    if not session:
        not_found("Session", session_id)
    
    # Verify question exists
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        not_found("Question", question_id)
    
    # Create directory for recordings if it doesn't exist
    upload_dir = os.path.join("uploads", "recordings")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    file_extension = os.path.splitext(audio_file.filename)[1]
    file_name = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(upload_dir, file_name)
    
    # Save audio file
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await audio_file.read()
            await out_file.write(content)
    except Exception as e:
        internal_error(f"Failed to save audio file: {str(e)}")
    
    # Create recording record with pending status for both transcription and analysis
    recording = Recording(
        session_id=session_id,
        question_id=question_id,
        file_path=file_path,
        transcription_status="pending",
        analysis_status="pending"
    )
    db.add(recording)
    db.commit()
    db.refresh(recording)
    
    # Process transcription and enhanced analysis in the background
    if settings.OPENAI_API_KEY:
        background_tasks.add_task(process_recording, db, recording.id, file_path)
    else:
        logger.warning("OPENAI_API_KEY not set. Skipping transcription and analysis.")
        recording.transcription_status = "skipped"
        recording.analysis_status = "skipped"
        db.commit()
    
    return recording