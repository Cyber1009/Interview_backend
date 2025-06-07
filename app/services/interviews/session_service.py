"""
Session service for the candidates domain.
Handles business logic related to candidate interview sessions.
"""
import logging
from datetime import datetime, timezone
from fastapi import HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database.models import Token, CandidateSession, Recording, Question

# Configure logging
logger = logging.getLogger(__name__)

class SessionService:
    """
    Service for handling interview session operations.
    Implements business logic for starting and completing sessions.
    """
    
    def start_session(self, token: Token, db: Session) -> CandidateSession:
        """
        Start a new interview session using a token with enhanced validation.
        This function assumes the token has already been verified and is valid.
        
        Args:
            token: The token object to use for starting the session
            db: Database session
            
        Returns:
            The created CandidateSession object
            
        Raises:
            HTTPException: If token not found
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found"
            )
        
        # Increment attempt counter
        token.current_attempts += 1
        
        # Mark token as used (backward compatibility)
        token.is_used = True
        db.commit()  # Commit the token update first
        
        # Create session
        session = CandidateSession(token_id=token.id)
        db.add(session)
        db.commit()  # Commit the session creation
        
        # Get the session with fresh data instead of using refresh
        new_session = db.query(CandidateSession).filter(CandidateSession.id == session.id).first()
        
        logger.info(f"Started new session {new_session.id} with token {token.token_value} (attempt {token.current_attempts}/{token.max_attempts})")
        return new_session
    
    def complete_session(self, session_id: int, db: Session) -> bool:
        """
        Mark a session as completed by setting the end time.
        
        Args:
            session_id: ID of the session to complete
            db: Database session
            
        Returns:
            True if session was successfully completed
            
        Raises:
            HTTPException: If session not found
        """
        # Find session
        session = db.query(CandidateSession).filter(CandidateSession.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with ID {session_id} not found"
            )
          # Set end time using timezone-aware datetime
        session.end_time = datetime.now(timezone.utc)
        db.commit()
        
        logger.info(f"Completed session {session.id}")
        return True
    
    def complete_session_by_token(self, token_value: str, db: Session, background_tasks: BackgroundTasks = None) -> bool:
        """
        Mark a session as completed by setting the end time, using the token value to identify the session.
        
        Args:
            token_value: The token value used to start the session
            db: Database session
            
        Returns:
            True if session was successfully completed
            
        Raises:
            HTTPException: If session not found for the given token
        """
        # Find token
        token = db.query(Token).filter(Token.token_value == token_value).first()
        if not token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Token not found"
            )
        
        # Find session associated with the token
        session = db.query(CandidateSession).filter(CandidateSession.token_id == token.id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No session found for this token"
            )
          # Set end time using timezone-aware datetime
        session.end_time = datetime.now(timezone.utc)
        db.commit()
        
        # Trigger batch analysis for all recordings in this session
        if background_tasks:
            self._trigger_batch_analysis(session.id, background_tasks, db)
        
        logger.info(f"Completed session {session.id} using token {token_value}")
        return True
    
    def _trigger_batch_analysis(self, session_id: int, background_tasks: BackgroundTasks, db: Session) -> None:
        """
        Trigger batch transcription and analysis for all recordings in a session.
        
        Args:
            session_id: ID of the completed session
            background_tasks: FastAPI background tasks
            db: Database session
        """
        try:
            # Get all recordings for this session
            recordings = db.query(Recording).filter(
                Recording.session_id == session_id,
                Recording.transcription_status == "pending"
            ).all()
            
            if not recordings:
                logger.info(f"No pending recordings found for session {session_id}")
                return
            
            logger.info(f"Triggering batch analysis for {len(recordings)} recordings in session {session_id}")
            
            # Add background task for batch processing
            background_tasks.add_task(self._process_session_batch, session_id, [r.id for r in recordings])
            
        except Exception as e:
            logger.error(f"Failed to trigger batch analysis for session {session_id}: {e}")
    
    async def _process_session_batch(self, session_id: int, recording_ids: list) -> None:
        """
        Process all recordings in a session as a batch.
        
        Args:
            session_id: ID of the session
            recording_ids: List of recording IDs to process
        """
        from backup.integrated_interview_service import IntegratedInterviewService
        
        # Create a new database session for background processing
        from app.core.database.db import SessionLocal
        db = SessionLocal()
        
        try:
            logger.info(f"Starting batch processing for session {session_id} with {len(recording_ids)} recordings")
            
            # Initialize integrated service for batch processing
            integrated_service = IntegratedInterviewService()
            
            transcripts = []
            questions = []
            
            # Process each recording for transcription first
            for recording_id in recording_ids:
                recording = db.query(Recording).filter(Recording.id == recording_id).first()
                if not recording:
                    continue
                
                # Transcribe the recording
                try:
                    transcription_result = integrated_service.transcription_service.transcribe_file(recording.file_path)
                    
                    if "error" not in transcription_result:
                        recording.transcript = transcription_result.get("text", "")
                        recording.transcription_status = "completed"
                        transcripts.append(recording.transcript)
                        
                        # Get question text for context
                        question = db.query(Question).filter(Question.id == recording.question_id).first()
                        questions.append(question.text if question else "")
                        
                    else:
                        recording.transcription_status = "failed"
                        recording.transcription_error = transcription_result.get("error", "Unknown error")
                        
                    db.add(recording)
                    
                except Exception as e:
                    logger.error(f"Failed to transcribe recording {recording_id}: {e}")
                    recording.transcription_status = "failed"
                    recording.transcription_error = str(e)[:500]
                    db.add(recording)
            
            db.commit()
              # Perform comprehensive session analysis if we have transcripts
            if transcripts:
                try:
                    # Prepare recordings data for comprehensive session analysis
                    recordings_data = []
                    for i, recording_id in enumerate(recording_ids):
                        recording = db.query(Recording).filter(Recording.id == recording_id).first()
                        if recording and recording.transcription_status == "completed":
                            question = db.query(Question).filter(Question.id == recording.question_id).first()
                            recordings_data.append({
                                'file_path': recording.file_path,
                                'question_text': question.text if question else f"Question {i+1}",
                                'recording_id': recording.id
                            })
                    
                    if recordings_data:
                        # Use comprehensive session processing for analysis
                        session_context = {
                            "session_id": session_id,
                            "analysis_type": "session_completion_batch"
                        }
                        
                        session_analysis = integrated_service.process_session_recordings(
                            recordings_data=recordings_data,
                            session_context=session_context
                        )
                        
                        logger.info(f"Comprehensive session analysis completed for session {session_id}")
                        logger.debug(f"Session analysis result: {session_analysis.get('status', 'unknown')}")
                    
                except Exception as e:
                    logger.error(f"Failed to perform comprehensive session analysis for session {session_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error in batch processing for session {session_id}: {e}")
        finally:
            db.close()
    
    def get_session(self, session_id: int, db: Session) -> CandidateSession:
        """
        Get a session by ID.
        
        Args:
            session_id: ID of the session
            db: Database session
            
        Returns:
            The CandidateSession object
            
        Raises:
            HTTPException: If session not found
        """
        session = db.query(CandidateSession).filter(CandidateSession.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with ID {session_id} not found"
            )
        return session
    def get_session_by_token(self, token_value: str, db: Session) -> CandidateSession:
        """
        Get an existing session by token value.
        
        Args:
            token_value: The token value to look up
            db: Database session
            
        Returns:
            The CandidateSession if found, None otherwise
        """
        token = db.query(Token).filter(Token.token_value == token_value).first()
        
        if not token:
            return None
            
        # Find the most recent session for this token
        session = db.query(CandidateSession).filter(
            CandidateSession.token_id == token.id
        ).order_by(CandidateSession.id.desc()).first()
        
        return session