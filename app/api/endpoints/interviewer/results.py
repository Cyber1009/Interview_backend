"""
Endpoints for retrieving and analyzing interview results.
Direct routes for interview results, mounted at /api/v1/interviewer/{interview_key}/results
"""
import logging
from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Union, Optional
import os
from datetime import datetime, timezone, timedelta

from app.api.dependencies import db_dependency, active_user_dependency
from app.core.database.models import User, Interview, CandidateSession, Recording, Token, Question
from app.schemas.interview_schemas import InterviewResult
from app.schemas.recording_schemas import RecordingDetails, RecordingResponse
from app.api.exceptions import not_found, forbidden
from app.core.database.repositories import InterviewRepository, SessionRepository, RecordingRepository
from app.utils.interview_utils import get_interview_by_key

# Add batch processing schemas
from pydantic import BaseModel

class BatchProcessRequest(BaseModel):
    """Request model for batch processing operations."""
    force_reprocess: bool = False

class BatchProcessResponse(BaseModel):
    """Response model for batch processing status."""
    session_id: int
    total_recordings: int
    processed_recordings: int
    failed_recordings: int
    status: str  # "processing", "completed", "completed_with_errors"
    message: str

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# SECTION: Results Retrieval

@router.get("", response_model=None)
def get_interview_results(
    interview_key: str,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
) -> Union[List[InterviewResult], JSONResponse]:
    """
    Get results for a specific interview.
    
    The interview_key can be either a numeric ID or a URL-friendly slug.
    """
    try:
        interview = get_interview_by_key(db, interview_key, current_user.id)
    except HTTPException as e:
        # Return a friendly message instead of 404 error
        return JSONResponse(
            status_code=200,
            content={
                "message": f"No interview found with identifier '{interview_key}' or you don't have permission to access it.",
                "results": []
            }
        )
    
    # Use a join to efficiently get sessions and their tokens in a single query
    sessions = (db.query(CandidateSession)
                .join(Token, CandidateSession.token_id == Token.id)
                .filter(Token.interview_id == interview.id)
                .all())
    
    # If no sessions found, return a friendly message
    if not sessions:
        return JSONResponse(
            status_code=200,
            content={
                "message": f"No results found for interview '{interview.title}'. No candidates have completed this interview yet.",
                "results": []
            }
        )
    
    results = []
    for session in sessions:
        # Use repository to get recordings for this session
        recordings = RecordingRepository.get_all_by_session(db, session.id)
        
        # Get token for this session - we can access it directly through the relationship
        token = db.query(Token).filter(Token.id == session.token_id).first()
        
        result = InterviewResult(
            session_id=session.id,
            token_value=token.token_value,
            start_time=session.start_time,
            end_time=session.end_time,
            recordings=recordings
        )
        
        results.append(result)
    
    return results

# SECTION: Individual Session Details

@router.get("/{session_id}", response_model=None)
def get_session_detail(
    interview_key: str,
    session_id: int,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
) -> Union[InterviewResult, JSONResponse]:
    """
    Get detailed information for a specific session.
    
    The interview_key can be either a numeric ID or a URL-friendly slug.
    """
    try:
        interview = get_interview_by_key(db, interview_key, current_user.id)
    except HTTPException as e:
        return JSONResponse(
            status_code=404,
            content={"message": f"Interview with identifier '{interview_key}' not found or access denied."}
        )
    
    # Get the specific session with its token
    session = (db.query(CandidateSession)
               .join(Token, CandidateSession.token_id == Token.id)
               .filter(
                   CandidateSession.id == session_id,
                   Token.interview_id == interview.id
               ).first())
    
    if not session:
        return JSONResponse(
            status_code=404,
            content={"message": f"Session {session_id} not found for this interview."}
        )
    
    # Get recordings for this session
    recordings = RecordingRepository.get_all_by_session(db, session.id)
    
    # Get token for this session
    token = db.query(Token).filter(Token.id == session.token_id).first()
    
    result = InterviewResult(
        session_id=session.id,
        token_value=token.token_value,
        start_time=session.start_time,
        end_time=session.end_time,
        recordings=recordings
    )
    
    return result

# SECTION: Recording Management

@router.get("/{session_id}/recordings/{recording_id}/download")
def download_recording(
    interview_key: str,
    session_id: int,
    recording_id: int,
    inline: bool = False,  # NEW: Add this parameter
    token: str = Query(None),  # NEW: Optional token parameter for direct access
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """
    Download or stream a specific recording file.
    
    Args:
        interview_key: The interview identifier (ID or slug)
        session_id: The candidate session ID
        recording_id: The recording ID
        inline: If True, sets headers for inline viewing (browser playback)
                If False, forces download with attachment headers
        token: Optional token parameter for direct URL access (bypasses session auth)
        db: Database session
        current_user: The authenticated user
        
    Returns:
        File response for downloading or streaming the recording
        
    Raises:
        HTTP 404: If interview, session, recording not found, or file doesn't exist
        HTTP 403: If user doesn't have permission to access the interview
    
    The interview_key can be either a numeric ID or a URL-friendly slug.
    """
    try:
        interview = get_interview_by_key(db, interview_key, current_user.id)
    except HTTPException as e:
        raise HTTPException(status_code=404, detail=f"Interview with identifier '{interview_key}' not found or access denied.")
    
    # Verify session belongs to interview
    session = (db.query(CandidateSession)
               .join(Token, CandidateSession.token_id == Token.id)
               .filter(
                   CandidateSession.id == session_id,
                   Token.interview_id == interview.id
               ).first())
    
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found for this interview.")
    
    # Get the specific recording
    recording = (db.query(Recording)
                .filter(
                    Recording.id == recording_id,
                    Recording.session_id == session.id
                ).first())
    
    if not recording:
        raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found for this session.")
      # Handle different storage types
    if recording.storage_type == "s3":
        # For S3 storage, generate a fresh presigned URL
        try:
            from app.services.storage.storage_factory import get_storage
            storage = get_storage()
            if hasattr(storage, 'get_url'):
                presigned_url = storage.get_url(recording.file_path, expires_in=3600)
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url=presigned_url)
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="S3 storage not properly configured"
                )
        except Exception as e:
            logger.error(f"Failed to generate S3 presigned URL for {recording.file_path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording file URL not available"
            )
    else:
        # For local storage, serve the file directly
        if not recording.file_path:
            raise HTTPException(status_code=404, detail="Recording file not available.")
        
        # Check if file exists
        file_path = recording.file_path
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Recording file not found on server.")
        
        # Determine the media type based on file extension
        file_extension = os.path.splitext(recording.file_path)[1].lower()
        media_type_map = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/mp4',
            '.ogg': 'audio/ogg',
            '.webm': 'audio/webm'
        }
        media_type = media_type_map.get(file_extension, 'audio/webm')
        
        # Generate filename
        filename = f"recording_question_{recording.question_id}_session_{session_id}{file_extension}"
        
        # NEW: Different headers based on inline parameter
        if inline:
            # For browser playback - inline streaming
            return FileResponse(
                path=file_path,
                media_type=media_type,
                headers={
                    "Content-Disposition": f"inline; filename={filename}",
                    "Accept-Ranges": "bytes",  # Enable seeking for video/audio
                    "Cache-Control": "private, max-age=3600",  # Cache for 1 hour
                    "X-Content-Type-Options": "nosniff",
                    "Access-Control-Allow-Origin": "*",  # Adjust based on your CORS policy
                    "Access-Control-Expose-Headers": "Content-Length, Content-Range"
                }
            )
        else:
            # For download - force attachment download
            return FileResponse(
                path=file_path,
                filename=filename,
                media_type=media_type,
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Cache-Control": "no-cache"  # Don't cache downloads
                }
            )

@router.get("/{session_id}/recordings/{recording_id}", response_model=RecordingResponse)
def get_recording_details(
    interview_key: str,
    session_id: int,
    recording_id: int,
    include_file_url: bool = Query(True, description="Include file URL in response (may trigger S3 operations)"),
    generate_url: bool = Query(False, description="Generate a fresh S3 URL (for S3 storage)"),
    expires_in: int = Query(3600, description="URL expiration time in seconds (when generate_url=true)"),
    inline: bool = Query(False, description="Whether URL should be for inline viewing or download (when generate_url=true)"),
    db: Session = db_dependency,
    current_user: User = active_user_dependency
) -> RecordingResponse:
    """
    Get detailed information for a specific recording.
    
    This consolidated endpoint replaces the previous data-only endpoint and URL generation endpoint.
    Use include_file_url=false for cost-optimized metadata-only requests.
    Use generate_url=true to generate a fresh S3 URL for the recording.
    
    Args:
        interview_key: The interview identifier (ID or slug)
        session_id: The candidate session ID
        recording_id: The recording ID
        include_file_url: Whether to include file URL (may trigger S3 operations for cost)
        generate_url: Whether to generate a fresh S3 URL for the recording
        expires_in: URL expiration time in seconds (when generate_url=true)
        inline: Whether URL should be for inline viewing or download (when generate_url=true)
        db: Database session
        current_user: The authenticated user
        
    Returns:
        Detailed recording information including transcript and analysis
        
    Raises:
        HTTP 404: If interview, session, or recording not found
        HTTP 403: If user doesn't have permission to access the interview
    """
    try:
        interview = get_interview_by_key(db, interview_key, current_user.id)
    except HTTPException as e:
        raise HTTPException(status_code=404, detail=f"Interview with identifier '{interview_key}' not found or access denied.")
    
    # Verify session belongs to interview
    session = (db.query(CandidateSession)
               .join(Token, CandidateSession.token_id == Token.id)
               .filter(
                   CandidateSession.id == session_id,
                   Token.interview_id == interview.id
               ).first())
    
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found for this interview.")
    
    # Get the specific recording and verify it belongs to this session
    recording = (db.query(Recording)
                .filter(
                    Recording.id == recording_id,
                    Recording.session_id == session.id
                ).first())
    
    if not recording:
        raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found for this session.")
    
    # Create a copy of the recording data for manipulation
    recording_data = RecordingResponse.model_validate(recording)
    
    # Cost optimization: Conditionally include file URL based on parameter
    if not include_file_url and hasattr(recording_data, 'file_url'):
        recording_data.file_url = None
    
    # URL generation if requested
    if generate_url and recording.storage_type == "s3":
        try:
            from app.services.storage.storage_factory import get_storage
            storage = get_storage()
            if hasattr(storage, 'get_url'):
                presigned_url = storage.get_url(recording.file_path, expires_in=expires_in)
                recording_data.file_url = presigned_url
            else:
                logger.warning("S3 storage configured but get_url method not available")
        except Exception as e:
            logger.error(f"Failed to generate S3 URL for recording {recording_id}: {str(e)}")
    
    return recording_data

# ======================================================================
# SECTION: Batch Processing (Cost-Optimized Operations)
# ======================================================================

@router.post("/{session_id}/batch-process", response_model=BatchProcessResponse)
def batch_process_session(
    interview_key: str,
    session_id: int,
    request: BatchProcessRequest,
    background_tasks: BackgroundTasks,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
) -> BatchProcessResponse:
    """
    Process all recordings for a candidate session in batch.
    
    This endpoint processes transcription and analysis for all recordings
    in a session efficiently, using existing batch processing capabilities.
    
    Benefits:
    - Reduced individual API calls
    - Batch optimization for cost savings
    - Centralized processing status tracking
    """
    try:
        interview = get_interview_by_key(db, interview_key, current_user.id)
    except HTTPException:
        raise HTTPException(status_code=404, detail=f"Interview with identifier '{interview_key}' not found or access denied.")
    
    # Verify session belongs to interview
    session = (db.query(CandidateSession)
               .join(Token, CandidateSession.token_id == Token.id)
               .filter(
                   CandidateSession.id == session_id,
                   Token.interview_id == interview.id
               ).first())
    
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found for this interview.")
    
    # Get all recordings for this session
    recordings = (db.query(Recording)
                  .filter(Recording.session_id == session.id)
                  .all())
    
    if not recordings:
        return BatchProcessResponse(
            session_id=session_id,
            total_recordings=0,
            processed_recordings=0,
            failed_recordings=0,
            status="completed",
            message="No recordings found for this session"
        )
    
    # Filter recordings based on force_reprocess flag
    if request.force_reprocess:
        recordings_to_process = recordings
    else:
        # Only process recordings that haven't been completed
        recordings_to_process = [
            r for r in recordings 
            if r.transcription_status in ["pending", "failed"] or 
               r.analysis_status in ["pending", "failed"]
        ]
    
    if not recordings_to_process:
        completed_count = len([r for r in recordings if r.transcription_status == "completed" and r.analysis_status == "completed"])
        return BatchProcessResponse(
            session_id=session_id,
            total_recordings=len(recordings),
            processed_recordings=completed_count,
            failed_recordings=0,
            status="completed",
            message="All recordings already processed"
        )
    
    # Start batch processing in background
    background_tasks.add_task(
        _process_session_recordings_batch,
        db,
        session_id,
        [r.id for r in recordings_to_process],
        request.force_reprocess
    )
    
    return BatchProcessResponse(
        session_id=session_id,
        total_recordings=len(recordings),
        processed_recordings=0,  # Will be updated as processing completes
        failed_recordings=0,
        status="processing",
        message=f"Started batch processing of {len(recordings_to_process)} recordings"
    )

@router.get("/{session_id}/batch-status", response_model=BatchProcessResponse)
def get_batch_process_status(
    interview_key: str,
    session_id: int,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
) -> BatchProcessResponse:
    """
    Get the current status of batch processing for a session.
    
    Returns current processing statistics and status for monitoring
    long-running batch operations.
    """
    try:
        interview = get_interview_by_key(db, interview_key, current_user.id)
    except HTTPException:
        raise HTTPException(status_code=404, detail=f"Interview with identifier '{interview_key}' not found or access denied.")
    
    # Verify session belongs to interview
    session = (db.query(CandidateSession)
               .join(Token, CandidateSession.token_id == Token.id)
               .filter(
                   CandidateSession.id == session_id,
                   Token.interview_id == interview.id
               ).first())
    
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found for this interview.")
    
    # Get all recordings and their status
    recordings = (db.query(Recording)
                  .filter(Recording.session_id == session.id)
                  .all())
    
    if not recordings:
        return BatchProcessResponse(
            session_id=session_id,
            total_recordings=0,
            processed_recordings=0,
            failed_recordings=0,
            status="completed",
            message="No recordings found for this session"
        )
    
    # Calculate status counts
    total_recordings = len(recordings)
    completed_recordings = len([
        r for r in recordings 
        if r.transcription_status == "completed" and r.analysis_status == "completed"
    ])
    failed_recordings = len([
        r for r in recordings 
        if r.transcription_status == "failed" or r.analysis_status == "failed"
    ])
    pending_recordings = total_recordings - completed_recordings - failed_recordings
    
    # Determine overall status
    if completed_recordings == total_recordings:
        status = "completed"
        message = "All recordings processed successfully"
    elif failed_recordings > 0 and pending_recordings == 0:
        status = "completed_with_errors"
        message = f"Processing completed with {failed_recordings} failures"
    elif pending_recordings > 0:
        status = "processing"
        message = f"Processing in progress: {pending_recordings} recordings remaining"
    else:
        status = "unknown"
        message = "Unable to determine processing status"
    
    return BatchProcessResponse(
        session_id=session_id,
        total_recordings=total_recordings,
        processed_recordings=completed_recordings,
        failed_recordings=failed_recordings,
        status=status,
        message=message
    )

# ======================================================================
# SECTION: Background Processing Functions (Smart Retry Logic)
# ======================================================================

async def _process_session_recordings_batch(
    db: Session,
    session_id: int,
    recording_ids: List[int],
    force_reprocess: bool = False
):
    """
    Background task to process all recordings in a session with smart retry logic.
    
    Implements different retry strategies based on failure type:
    - Transcription failures: Exponential backoff with max 3 retries
    - Analysis failures: Immediate retry with different model if available
    - File access failures: Shorter retry intervals
    """
    logger.info(f"Starting batch processing for session {session_id} with {len(recording_ids)} recordings")
    
    for recording_id in recording_ids:
        try:
            # Get fresh recording data
            recording = db.query(Recording).filter(Recording.id == recording_id).first()
            if not recording:
                logger.warning(f"Recording {recording_id} not found during batch processing")
                continue
            
            # Process transcription if needed
            if force_reprocess or recording.transcription_status in ["pending", "failed"]:
                await _process_recording_transcription(db, recording, force_reprocess)
            
            # Process analysis if transcription is complete
            if recording.transcription_status == "completed" and recording.transcript:
                if force_reprocess or recording.analysis_status in ["pending", "failed"]:
                    await _process_recording_analysis(db, recording, force_reprocess)
            
        except Exception as e:
            logger.error(f"Failed to process recording {recording_id} in batch: {str(e)}")
            # Update recording with error status
            try:
                recording = db.query(Recording).filter(Recording.id == recording_id).first()
                if recording:
                    recording.transcription_status = "failed"
                    recording.transcription_error = f"Batch processing error: {str(e)}"
                    db.commit()
            except Exception as db_error:
                logger.error(f"Failed to update recording error status: {str(db_error)}")
    
    logger.info(f"Completed batch processing for session {session_id}")

async def _process_recording_transcription(
    db: Session,
    recording: Recording,
    force_reprocess: bool
):
    """
    Process transcription with smart retry logic.
    """
    try:
        # Update status to indicate processing
        recording.transcription_status = "processing"
        db.commit()
        
        # Import transcription service locally to avoid circular imports
        from app.services.transcription.transcription_service import TranscriptionService
        transcription_service = TranscriptionService()
        
        # Attempt transcription
        transcript = await transcription_service.transcribe_audio(
            recording.file_path,
            recording.storage_type
        )
        
        if transcript:
            recording.transcript = transcript
            recording.transcription_status = "completed"
            recording.transcription_error = None
            if hasattr(recording, 'transcription_retry_count'):
                recording.transcription_retry_count = 0  # Reset retry count on success
        else:
            raise Exception("Empty transcript returned")
            
    except Exception as e:
        error_message = str(e)
        logger.error(f"Transcription failed for recording {recording.id}: {error_message}")
        
        # Implement smart retry logic based on error type
        retry_count = getattr(recording, 'transcription_retry_count', 0)
        
        if "file not found" in error_message.lower() or "access denied" in error_message.lower():
            # File access errors - shorter retry interval
            recording.transcription_status = "retry_scheduled" if retry_count < 3 else "failed"
            if hasattr(recording, 'next_retry_at'):
                recording.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        elif "rate limit" in error_message.lower() or "quota" in error_message.lower():
            # Rate limit errors - longer retry interval
            recording.transcription_status = "retry_scheduled" if retry_count < 3 else "failed"
            if hasattr(recording, 'next_retry_at'):
                recording.next_retry_at = datetime.now(timezone.utc) + timedelta(hours=1)
        else:
            # General errors - exponential backoff
            retry_delay_minutes = min(60, 5 * (2 ** retry_count))
            recording.transcription_status = "retry_scheduled" if retry_count < 3 else "failed"
            if hasattr(recording, 'next_retry_at'):
                recording.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=retry_delay_minutes)
        
        recording.transcription_error = error_message[:500]  # Truncate long errors
        if hasattr(recording, 'transcription_retry_count'):
            recording.transcription_retry_count = retry_count + 1
        
        # Mark as failed if too many retries
        if retry_count >= 3:
            recording.transcription_status = "failed"
            if hasattr(recording, 'next_retry_at'):
                recording.next_retry_at = None
    
    finally:
        db.commit()

async def _process_recording_analysis(
    db: Session,
    recording: Recording,
    force_reprocess: bool
):
    """
    Process analysis with smart retry logic.
    """
    try:
        # Update status to indicate processing
        recording.analysis_status = "processing"
        db.commit()
        
        # Import analysis service locally to avoid circular imports
        from app.services.analysis.analysis_service import AnalysisService
        analysis_service = AnalysisService()
        
        # Get question text for context
        question = db.query(Question).filter(Question.id == recording.question_id).first()
        question_text = question.text if question else None
        
        # Attempt analysis using the analysis service
        analysis_result = await analysis_service.analyze_response(
            recording.transcript,
            question_text
        )
        
        if analysis_result and "error" not in analysis_result:
            import json
            recording.analysis = json.dumps(analysis_result)
            recording.analysis_status = "completed"
            recording.analysis_error = None
        else:
            error_msg = analysis_result.get("error", "Unknown analysis error") if analysis_result else "No analysis result"
            raise Exception(error_msg)
            
    except Exception as e:
        error_message = str(e)
        logger.error(f"Analysis failed for recording {recording.id}: {error_message}")
        
        # For analysis errors, try immediate retry with different approach if available
        if "rate limit" in error_message.lower():
            if hasattr(recording, 'next_retry_at'):
                recording.analysis_status = "retry_scheduled"
                recording.next_retry_at = datetime.now(timezone.utc) + timedelta(hours=1)
            else:
                recording.analysis_status = "failed"
        else:
            recording.analysis_status = "failed"
        
        recording.analysis_error = error_message[:500]
    
    finally:
        db.commit()

# SECTION: Results Management