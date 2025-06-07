"""
Transcription services for local Whisper processing and OpenAI analysis.
"""
from app.services.transcription.transcription_service import TranscriptionService

# Create singleton instance
transcription_service = TranscriptionService()

__all__ = ["TranscriptionService", "transcription_service"]