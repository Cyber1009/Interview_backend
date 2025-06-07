"""
Transcription Service
Handles audio transcription using OpenAI Whisper with local model support
"""
import json
import logging
import asyncio
import whisper
import openai
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database.models import Recording, CandidateSession
from app.services.storage.storage_factory import get_storage

# Configure logging
logger = logging.getLogger(__name__)

class TranscriptionService:
    """
    Service for transcribing audio recordings using OpenAI Whisper.
    Delegates analysis to the dedicated analysis service.
    """
    
    def __init__(self):
        """Initialize the transcription service."""
        self.model = None
        
    def _get_whisper_model(self):
        """Get Whisper model (lazy loading)."""
        if self.model is None:
            try:
                self.model = whisper.load_model("base")
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {str(e)}")
                raise
        return self.model

    async def transcribe_recording(self, recording_id: int, db: Session) -> bool:
        """
        Transcribe a single recording.
        
        Args:
            recording_id: Recording ID
            db: Database session
            
        Returns:
            Success status
        """
        try:
            # Get recording from database
            recording = db.query(Recording).filter(Recording.id == recording_id).first()
            if not recording:
                logger.error(f"Recording {recording_id} not found")
                return False
            
            if not recording.file_path:
                logger.error(f"Recording {recording_id} has no file path")
                recording.transcription_status = "failed"
                recording.transcription_error = "No file path available"
                db.commit()
                return False
            
            # Update status to processing
            recording.transcription_status = "processing"
            recording.transcription_started_at = datetime.now(timezone.utc)
            db.commit()
            
            logger.info(f"Starting transcription for recording {recording_id}")
            
            # Download file for transcription
            local_file_path = await self._download_recording_for_transcription(recording)
            if not local_file_path:
                recording.transcription_status = "failed"
                recording.transcription_error = "Failed to download file for transcription"
                db.commit()
                return False
            
            # Perform transcription using local Whisper
            try:
                model = self._get_whisper_model()
                result = model.transcribe(local_file_path)
                  # Prepare transcript data with detailed segments
                segments = result.get("segments", [])
                if segments:
                    duration = segments[-1].get("end", 0.0)
                else:
                    duration = 0.0
                    
                transcript_data = {
                    "text": result["text"],
                    "language": result.get("language", "unknown"),
                    "duration": duration,
                    "segments": segments
                }
                
                # Store transcript in database
                recording.transcript = json.dumps(transcript_data)
                recording.transcription_status = "completed"
                recording.transcription_completed_at = datetime.now(timezone.utc)
                recording.transcription_error = None
                db.commit()
                logger.info(f"Transcription completed for recording {recording_id}")
                return True
            except Exception as e:
                error_msg = f"Transcription failed: {str(e)}"
                logger.error(f"Transcription error for recording {recording_id}: {error_msg}")
                
                recording.transcription_status = "failed"
                recording.transcription_error = error_msg[:500]  # Truncate long errors
                db.commit()
                return False
                
            finally:
                # Clean up temporary file if it was created
                if 'local_file_path' in locals() and local_file_path and recording.storage_type == "s3":
                    try:
                        os.unlink(local_file_path)
                        logger.debug(f"Cleaned up temporary file: {local_file_path}")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to clean up temporary file {local_file_path}: {cleanup_error}")
                        
        except Exception as e:
            logger.error(f"Unexpected error in transcription for recording {recording_id}: {str(e)}")
            return False

    async def _download_recording_for_transcription(self, recording: Recording) -> Optional[str]:
        """
        Download recording file for transcription.
        
        Args:
            recording: Recording object
            
        Returns:
            Local file path if successful, None if failed
        """
        try:
            if recording.storage_type == "s3":
                # Download from S3 storage
                storage = get_storage()
                if hasattr(storage, 'download_bytes'):
                    # Download file bytes from S3
                    file_bytes = await storage.download_bytes(recording.file_path)
                    
                    # Create temporary local file for transcription
                    import tempfile
                    import os
                    file_extension = os.path.splitext(recording.file_path)[1] or '.wav'
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                        temp_file.write(file_bytes)
                        temp_file_path = temp_file.name
                    
                    logger.info(f"Downloaded S3 file to temporary location: {temp_file_path}")
                    return temp_file_path
                else:
                    logger.error("S3 storage does not support download_bytes method")
                    return None
            else:
                # For local storage, file_path should be the direct local path
                if os.path.exists(recording.file_path):
                    return recording.file_path
                else:
                    logger.error(f"Local file not found: {recording.file_path}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to download recording {recording.id}: {str(e)}")
            return None

    async def transcribe_session_recordings(self, session_id: int, db: Session) -> List[Dict[str, Any]]:
        """
        Transcribe all recordings for a session.
        
        Args:
            session_id: Session ID
            db: Database session
            
        Returns:
            List of transcription results
        """
        # Get all recordings for the session
        recordings = db.query(Recording).filter(Recording.session_id == session_id).all()
        
        if not recordings:
            logger.warning(f"No recordings found for session {session_id}")
            return []
        
        logger.info(f"Starting transcription for {len(recordings)} recordings in session {session_id}")
        
        # Create transcription tasks
        tasks = []
        for recording in recordings:
            if recording.transcription_status in ["completed", "processing"]:
                logger.info(f"Skipping recording {recording.id} - already {recording.transcription_status}")
                continue
            tasks.append(self.transcribe_recording(recording.id, db))
        
        # Execute transcriptions in parallel (with limit)
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results = []
        
        # Prepare results summary
        transcription_results = []
        for recording, result in zip(recordings, results):
            if isinstance(result, Exception):
                logger.error(f"Exception in transcription for recording {recording.id}: {result}")
                success = False
            else:
                success = result
            
            transcription_results.append({
                "recording_id": recording.id,
                "question_id": recording.question_id,
                "success": success,
                "status": recording.transcription_status
            })
        logger.info(f"Transcription completed for session {session_id}. "
                   f"Success: {sum(1 for r in transcription_results if r['success'])}, "
                   f"Failed: {sum(1 for r in transcription_results if not r['success'])}")
        
        return transcription_results

    async def process_session_complete(self, session_id: int, db: Session) -> Dict[str, Any]:
        """
        Complete workflow: transcribe all recordings then delegate analysis to analysis service.
        
        Args:
            session_id: Session ID
            db: Database session
            
        Returns:
            Complete processing results
        """
        try:
            logger.info(f"Starting complete processing for session {session_id}")
            
            # Step 1: Transcribe all recordings
            transcription_results = await self.transcribe_session_recordings(session_id, db)
            
            # Step 2: Delegate analysis to analysis service
            from app.services.analysis.analysis_service import analysis_service
            analysis_result = await analysis_service.analyze_session_transcripts(session_id, db)
            
            return {
                "session_id": session_id,
                "transcription_results": transcription_results,
                "analysis_result": analysis_result,
                "status": "completed",
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Complete processing failed for session {session_id}: {str(e)}")
            return {
                "session_id": session_id,
                "status": "failed",
                "error": str(e),
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
    
    def get_session_transcription_status(self, session_id: int, db: Session) -> Dict[str, Any]:
        """
        Get transcription status summary for a session.
        
        Args:
            session_id: Session ID
            db: Database session
            
        Returns:
            Status summary
        """
        recordings = db.query(Recording).filter(Recording.session_id == session_id).all()
        
        if not recordings:
            return {"error": "No recordings found for session"}
        
        status_counts = {}
        for recording in recordings:
            status = recording.transcription_status or "pending"
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "session_id": session_id,
            "total_recordings": len(recordings),
            "status_breakdown": status_counts,
            "completed_percentage": (status_counts.get("completed", 0) / len(recordings)) * 100,            "ready_for_analysis": status_counts.get("completed", 0) == len(recordings)
        }

    def transcribe_file(self, file_path: str) -> Dict[str, Any]:
        """
        Transcribe a file directly (for testing purposes).
        
        Args:
            file_path: Path to the audio/video file
            
        Returns:
            Dict with transcription results
        """
        try:
            if not os.path.exists(file_path):
                return {"error": f"File not found: {file_path}"}
              # Load and transcribe using local Whisper model
            model = self._get_whisper_model()
            result = model.transcribe(file_path)
            
            # Calculate duration from segments if available
            segments = result.get("segments", [])
            if segments:
                # Use the end time of the last segment as total duration
                duration = segments[-1].get("end", 0.0)
            else:
                duration = 0.0
            
            return {
                "text": result["text"],
                "language": result.get("language", "unknown"),
                "duration": duration,
                "segments": segments
            }
            
        except Exception as e:
            logger.error(f"Direct transcription failed for {file_path}: {str(e)}")
            return {"error": f"Transcription failed: {str(e)}"}

# Create singleton instance
transcription_service = TranscriptionService()
