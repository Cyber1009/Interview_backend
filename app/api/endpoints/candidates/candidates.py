"""
Endpoints for candidate interview process.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks, File, Form, UploadFile, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict
import logging
from datetime import datetime, timezone
import os
import json
import uuid
import openai
import aiofiles

from app.api.deps import db_dependency
from app.core.config import settings
from app.schemas.interview_schemas import TokenVerify as CandidateTokenVerification
from app.schemas.interview_schemas import SessionStart as CandidateSessionCreate
from app.schemas.interview_schemas import TokenVerifyResponse, SessionResponse, InterviewResponse
from app.schemas.recording_schemas import RecordingResponse
from app.core.database.models import Token, Interview, CandidateSession, Recording, Question
from app.utils.error_utils import not_found, bad_request, internal_error

# Create router
candidates_router = APIRouter()

# Helper function for background transcription processing
async def process_transcription(db: Session, recording_id: int, file_path: str):
    """
    Process audio transcription in the background.
    This function is designed to be run as a background task.
    """
    try:
        openai.api_key = settings.OPENAI_API_KEY
        
        with open(file_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
        
        # Get a fresh db session for this background task
        recording = db.query(Recording).filter(Recording.id == recording_id).first()
        if recording:
            recording.transcript = transcript.text
            recording.transcription_status = "completed"
            db.commit()
    except Exception as e:
        # Log error but continue
        print(f"Error transcribing audio (ID: {recording_id}): {str(e)}")
        recording = db.query(Recording).filter(Recording.id == recording_id).first()
        if recording:
            recording.transcription_status = "failed"
            recording.transcription_error = str(e)[:500]  # Truncate very long error messages
            db.commit()

@candidates_router.post("/verify-token", 
                       response_model=TokenVerifyResponse,
                       summary="Verify Interview Token",
                       description="Verify if a candidate token is valid and has not been used")
def verify_token(
    token_data: CandidateTokenVerification,
    db: Session = db_dependency
):
    """
    Verify if a candidate token is valid and not already used.
    
    This is the first step in the candidate interview flow:
    1. Candidate enters their access token
    2. System verifies the token is valid
    3. If valid, candidate proceeds to start session
    
    Parameters:
    - **token_data**: Contains the token string to verify
    
    Returns:
    - **valid**: Boolean indicating if token is valid
    - **interview_id**: ID of associated interview if token is valid
    """
    token = db.query(Token).filter(
        Token.token_value == token_data.token,
        Token.is_used == False
    ).first()
    
    if not token:
        return {"valid": False}
    
    return {"valid": True, "interview_id": token.interview_id}

@candidates_router.post("/session", 
                      response_model=SessionResponse, 
                      summary="Start Interview Session",
                      description="Start a new interview session using a valid access token")
def start_session(
    session_data: CandidateSessionCreate,
    db: Session = db_dependency
):
    """
    Start a new interview session using a valid token.
    
    The token is marked as used, and a new session is created for the candidate.
    Each token can only be used to start one session.
    
    Parameters:
    - **session_data**: Contains the token to use for starting the session
    
    Returns:
    - Session details including ID and start time
    
    Raises:
    - HTTP 400: If token is invalid or already used
    """
    # Verify token
    token = db.query(Token).filter(
        Token.token_value == session_data.token,
        Token.is_used == False
    ).first()
    
    if not token:
        bad_request("Invalid or used token")
    
    # Mark token as used
    token.is_used = True
    
    # Create session
    session = CandidateSession(token_id=token.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session

@candidates_router.get("/interview/{token}", 
                     response_model=InterviewResponse,
                     summary="Get Interview Details",
                     description="Get interview details and questions using a valid token")
def get_interview_by_token(
    token: str,
    db: Session = db_dependency
):
    """
    Get interview details and questions using a valid token.
    
    This endpoint allows candidates to retrieve all interview details including:
    - Interview title
    - All questions with their text and timing parameters
    
    Parameters:
    - **token**: The access token string
    
    Returns:
    - Complete interview details including all questions
    
    Raises:
    - HTTP 404: If token or interview not found
    """
    # Get token object
    token_obj = db.query(Token).filter(Token.token_value == token).first()
    
    if not token_obj:
        not_found("Token", token)
    
    # Get interview
    interview = db.query(Interview).filter(Interview.id == token_obj.interview_id).first()
    
    if not interview:
        not_found("Interview", token_obj.interview_id)
    
    return interview

@candidates_router.post("/recordings", 
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
    
    Parameters:
    - **session_id**: ID of the active candidate session
    - **question_id**: ID of the question being answered
    - **audio_file**: The audio recording file
    
    Returns:
    - Recording details including ID and file path. Transcript will be added later.
    
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
    
    # Create recording record with a pending transcription status
    recording = Recording(
        session_id=session_id,
        question_id=question_id,
        file_path=file_path,
        transcription_status="pending"
    )
    db.add(recording)
    db.commit()
    db.refresh(recording)
    
    # Process transcription in the background
    if settings.OPENAI_API_KEY:
        background_tasks.add_task(process_transcription, db, recording.id, file_path)
    
    return recording

@candidates_router.post("/session/{session_id}/complete",
                      summary="Complete Interview Session",
                      description="Mark an interview session as completed",
                      response_model=Dict[str, str])
def complete_session(
    session_id: int = Path(..., description="ID of the session to complete"),
    db: Session = db_dependency
):
    """
    Mark a session as completed by setting the end time.
    
    This should be called when a candidate finishes their interview session.
    Once marked as complete, the session's recordings become available in the results.
    
    Parameters:
    - **session_id**: ID of the session to complete (path parameter)
    
    Returns:
    - Success message
    
    Raises:
    - HTTP 404: If session not found
    """
    session = db.query(CandidateSession).filter(CandidateSession.id == session_id).first()
    
    if not session:
        not_found("Session", session_id)
    
    session.end_time = datetime.utcnow()
    db.commit()
    
    return {"message": "Session completed successfully"}