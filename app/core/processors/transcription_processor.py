"""
Processor for transcribing audio/video interview recordings using OpenAI Whisper.
"""
import os
import logging
import openai
from typing import Dict, Any, Optional
from pathlib import Path
import tempfile

from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class TranscriptionProcessor:
    """Processor for transcribing audio/video interview recordings using OpenAI Whisper."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the transcription processor with OpenAI API key."""
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            logger.warning("No OpenAI API key provided. Transcription will not work.")
        else:
            openai.api_key = self.api_key
    
    def transcribe_file(self, file_path: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Transcribe an audio/video file using OpenAI Whisper API.
        
        Args:
            file_path: Path to the audio/video file
            options: Dictionary of options for the transcription
                - model: The model to use (e.g., "whisper-1")
                - language: Optional language code
                - prompt: Optional prompt for the transcription
                - temperature: Sampling temperature (0.0 to 1.0)
                
        Returns:
            Dictionary containing transcription results
        """
        if not self.api_key:
            logger.error("Transcription attempted but no API key available")
            return {"error": "Transcription service is not configured"}
            
        options = options or {}
        model = options.get("model", "whisper-1")  # Default to whisper-1 model
        
        try:
            # Process with Whisper API
            with open(file_path, "rb") as audio_file:
                transcription_params = {
                    "model": model,
                    "file": audio_file
                }
                
                # Add optional parameters if provided
                if "language" in options:
                    transcription_params["language"] = options["language"]
                if "prompt" in options:
                    transcription_params["prompt"] = options["prompt"]
                if "temperature" in options:
                    transcription_params["temperature"] = options["temperature"]
                    
                response = openai.Audio.transcribe(**transcription_params)
                
            return {
                "text": response.get("text", ""),
                "duration": response.get("duration", 0),
                "language": response.get("language", None),
                "model_used": model
            }
                
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return {"error": f"Transcription failed: {str(e)}"}