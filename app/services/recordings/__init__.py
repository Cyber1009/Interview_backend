"""
Recording services for handling S3 uploads, local Whisper transcription, and OpenAI analysis.
"""
from app.services.recordings.recording_service import RecordingService

# Create singleton instance
recording_service = RecordingService()

__all__ = ["RecordingService", "recording_service"]