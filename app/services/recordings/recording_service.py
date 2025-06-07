"""
Consolidated recording service for S3 upload, local Whisper transcription, and OpenAI analysis.
"""
import os
import logging
import json
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database.models import Recording, CandidateSession, Question
from app.services.storage.storage_factory import get_storage
from app.services.transcription import transcription_service

logger = logging.getLogger(__name__)

class RecordingService:
    """Consolidated service for recording upload, transcription, and analysis."""
    
    def __init__(self):
        self.storage = get_storage()
    
    # SECTION 1: Upload Operations
    async def save_recording_by_token(
        self, 
        token: str, 
        question_id: int, 
        file_content: bytes, 
        file_extension: str, 
        db: Session
    ) -> Recording:
        """Upload recording to S3 and save metadata to database."""
        try:
            # Find session by token
            session = db.query(CandidateSession).filter(
                CandidateSession.session_token == token,
                CandidateSession.is_active == True
            ).first()
            
            if not session:
                raise ValueError(f"No active session found for token: {token}")
            
            # Validate question exists
            question = db.query(Question).filter(Question.id == question_id).first()
            if not question:
                raise ValueError(f"Question {question_id} not found")
              # Generate unique filename prefix
            prefix = f"session_{session.id}_question_{question_id}"
            
            # Upload to storage using the storage adapter interface
            file_path = await self.storage.save(file_content, prefix, file_extension)
            
            # Create recording record
            recording = Recording(
                session_id=session.id,
                question_id=question_id,
                file_path=file_path,
                file_size=len(file_content),
                storage_type="s3" if settings.should_use_s3 else "local",
                transcription_status="pending",
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(recording)
            db.commit()
            db.refresh(recording)
            
            logger.info(f"Recording saved successfully: {recording.id} for session {session.id}")
            return recording
            
        except Exception as e:
            logger.error(f"Error saving recording for token {token}: {str(e)}")
            db.rollback()
            raise
    
    # SECTION 2: Transcription Operations  
    async def transcribe_recording(self, recording_id: int, db: Session) -> bool:
        """Transcribe a single recording using local Whisper."""
        return await transcription_service.transcribe_recording(recording_id, db)
        
    async def transcribe_session_recordings(self, session_id: int, db: Session) -> List[Dict]:
        """Transcribe all recordings for a session."""
        return await transcription_service.transcribe_session_recordings(session_id, db)
        
    # SECTION 3: Analysis Operations
    async def analyze_session_transcripts(self, session_id: int, db: Session) -> Dict[str, Any]:
        """Analyze all transcripts for a session using OpenAI."""
        return await transcription_service.analyze_session_transcripts(session_id, db)
        
    # SECTION 4: Batch Operations
    async def process_session_complete(self, session_id: int, db: Session):
        """Complete workflow: transcribe all recordings then analyze together."""
        return await transcription_service.process_session_complete(session_id, db)
    
    # SECTION 5: URL Operations (from optimized_url_service)
    def get_recording_url(self, recording: Recording, expires_in: int = 3600) -> Optional[str]:
        """Generate S3 presigned URL for recording access."""
        try:
            if recording.storage_type != "s3":
                logger.warning(f"Cannot generate URL for storage type: {recording.storage_type}")
                return None
            
            return self.storage.generate_presigned_url(
                file_path=recording.file_path,
                expires_in=expires_in
            )
        except Exception as e:
            logger.error(f"Error generating presigned URL for recording {recording.id}: {str(e)}")
            return None
    
    def get_recording_urls_batch(self, recordings: List[Recording], expires_in: int = 3600) -> Dict[int, Optional[str]]:
        """Generate presigned URLs for multiple recordings."""
        urls = {}
        for recording in recordings:
            urls[recording.id] = self.get_recording_url(recording, expires_in)
        return urls
    
    # SECTION 6: Recording Management Operations
    def get_session_recordings(self, session_id: int, db: Session) -> List[Recording]:
        """Get all recordings for a session."""
        return db.query(Recording).filter(Recording.session_id == session_id).all()
    
    def get_recording_by_id(self, recording_id: int, db: Session) -> Optional[Recording]:
        """Get recording by ID."""
        return db.query(Recording).filter(Recording.id == recording_id).first()
    
    def get_session_recording_status(self, session_id: int, db: Session) -> Dict[str, Any]:
        """Get recording and transcription status for a session."""
        recordings = self.get_session_recordings(session_id, db)
        
        if not recordings:
            return {
                "session_id": session_id,
                "total_recordings": 0,
                "status": "no_recordings"
            }
        
        # Count by transcription status
        status_counts = {}
        for recording in recordings:
            status = recording.transcription_status or "pending"
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Check if session analysis is complete
        session = db.query(CandidateSession).filter(CandidateSession.id == session_id).first()
        analysis_status = getattr(session, 'analysis_status', 'pending') if session else 'unknown'
        
        return {
            "session_id": session_id,
            "total_recordings": len(recordings),
            "transcription_status_breakdown": status_counts,
            "transcription_completed": status_counts.get("completed", 0),
            "transcription_failed": status_counts.get("failed", 0),
            "transcription_pending": status_counts.get("pending", 0),
            "transcription_percentage": (status_counts.get("completed", 0) / len(recordings)) * 100,
            "all_transcribed": status_counts.get("completed", 0) == len(recordings),
            "analysis_status": analysis_status,
            "ready_for_analysis": status_counts.get("completed", 0) == len(recordings) and analysis_status == "pending"
        }
    
    # SECTION 7: Cleanup Operations
    def delete_recording(self, recording_id: int, db: Session) -> bool:
        """Delete recording from both S3 and database."""
        try:
            recording = self.get_recording_by_id(recording_id, db)
            if not recording:
                logger.warning(f"Recording {recording_id} not found for deletion")
                return False
            
            # Delete from S3
            if recording.storage_type == "s3":
                delete_success = self.storage.delete_file(recording.file_path)
                if not delete_success:
                    logger.warning(f"Failed to delete file from S3: {recording.file_path}")
            
            # Delete from database
            db.delete(recording)
            db.commit()
            
            logger.info(f"Recording {recording_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting recording {recording_id}: {str(e)}")
            db.rollback()
            return False
    
    def cleanup_session_recordings(self, session_id: int, db: Session) -> Dict[str, Any]:
        """Delete all recordings for a session."""
        try:
            recordings = self.get_session_recordings(session_id, db)
            
            if not recordings:
                return {
                    "session_id": session_id,
                    "deleted_count": 0,
                    "status": "no_recordings_found"
                }
            
            deleted_count = 0
            failed_deletes = []
            
            for recording in recordings:
                if self.delete_recording(recording.id, db):
                    deleted_count += 1
                else:
                    failed_deletes.append(recording.id)
            
            return {
                "session_id": session_id,
                "total_recordings": len(recordings),
                "deleted_count": deleted_count,
                "failed_deletes": failed_deletes,
                "status": "completed" if not failed_deletes else "partial_failure"
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up recordings for session {session_id}: {str(e)}")
            return {
                "session_id": session_id,
                "status": "error",
                "error": str(e)
            }
    
    # SECTION 8: Validation and Health Check Operations
    def validate_recording_integrity(self, recording_id: int, db: Session) -> Dict[str, Any]:
        """Validate that recording exists in both database and S3."""
        try:
            recording = self.get_recording_by_id(recording_id, db)
            if not recording:
                return {
                    "recording_id": recording_id,
                    "status": "not_found_in_database"
                }
            
            # Check if file exists in S3
            if recording.storage_type == "s3":
                file_exists = self.storage.file_exists(recording.file_path)
                file_size = self.storage.get_file_size(recording.file_path) if file_exists else None
                
                return {
                    "recording_id": recording_id,
                    "database_record": True,
                    "file_exists_in_storage": file_exists,
                    "file_size_match": file_size == recording.file_size if file_size else False,
                    "storage_file_size": file_size,
                    "database_file_size": recording.file_size,
                    "status": "valid" if file_exists and (file_size == recording.file_size) else "invalid"
                }
            else:
                return {
                    "recording_id": recording_id,
                    "status": "unsupported_storage_type",
                    "storage_type": recording.storage_type
                }
                
        except Exception as e:
            logger.error(f"Error validating recording {recording_id}: {str(e)}")
            return {
                "recording_id": recording_id,
                "status": "validation_error",
                "error": str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health and dependencies."""
        health_status = {
            "service": "RecordingService",
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Check storage connection
            storage_healthy = self.storage.health_check() if hasattr(self.storage, 'health_check') else True
            health_status["checks"]["storage"] = "healthy" if storage_healthy else "unhealthy"
            
            # Check transcription service
            transcription_healthy = hasattr(transcription_service, 'process_session_complete')
            health_status["checks"]["transcription_service"] = "healthy" if transcription_healthy else "unhealthy"
            
            # Overall status
            if not all(status == "healthy" for status in health_status["checks"].values()):
                health_status["status"] = "degraded"
                
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status

# Create the service instance
recording_service = RecordingService()