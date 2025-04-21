"""
Enhanced processor for analyzing interview transcriptions using LLMs with scoring and detailed assessment.
"""
import os
import logging
import json
import openai
from typing import Dict, Any, Optional, List

from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class AnalysisProcessor:
    """Processor for analyzing interview transcriptions using LLMs with enhanced assessment."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the analysis processor with OpenAI API key."""
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            logger.warning("No OpenAI API key provided. Analysis will not work.")
        else:
            openai.api_key = self.api_key
    
    def analyze_interview(self, 
                          transcript: str,
                          question_text: Optional[str] = None,
                          model: str = "gpt-3.5-turbo") -> Dict[str, Any]:
        """
        Analyze an interview transcript to extract insights with enhanced scoring and assessment.
        
        Args:
            transcript: The interview transcript text
            question_text: Optional text of the question that was asked
            model: The model to use for analysis
            
        Returns:
            Dictionary containing detailed analysis results with scoring
        """
        if not self.api_key:
            logger.error("Analysis attempted but no API key available")
            return {"error": "Analysis service is not configured"}
            
        if not transcript:
            logger.warning("Empty transcript provided for analysis")
            return {"error": "Transcript is empty"}
        
        try:
            # Enhanced system message with scoring criteria
            system_message = """You are an expert interview evaluator. Analyze the candidate's response to the given question.

Evaluate the following aspects:
1. Relevance to the question (How directly did they address what was asked?)
2. Technical accuracy (Are the technical details correct and appropriate?)
3. Clarity of communication (How well articulated is the response?)
4. Depth of understanding (Does the candidate show deep knowledge?)
5. Practical application (Do they connect theory to practical scenarios?)

Format your response as JSON with the following structure:
{
    "key_insights": ["insight1", "insight2", ...],
    "strengths": ["strength1", "strength2", ...],
    "weaknesses": ["weakness1", "weakness2", ...],
    "scores": {
        "relevance": <score from 1-10>,
        "technical_accuracy": <score from 1-10>,
        "communication": <score from 1-10>,
        "understanding": <score from 1-10>,
        "practical_application": <score from 1-10>
    },
    "overall_score": <average of all scores, from 1-10>,
    "response_quality": "Excellent|Good|Average|Poor|Insufficient",
    "overall_assessment": "...",
    "improvement_suggestions": ["suggestion1", "suggestion2", ...]
}
"""
            
            # Always include the question if available for better context
            if question_text:
                user_content = f"Question asked: {question_text}\n\nCandidate's response:\n{transcript}"
            else:
                user_content = f"Interview Response:\n{transcript}"
            
            # Call the OpenAI API for analysis with enhanced prompt
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"}
            )
            
            # Extract and parse the analysis
            analysis_text = response.choices[0].message.content
            try:
                analysis = json.loads(analysis_text)
            except json.JSONDecodeError:
                logger.error("Failed to parse analysis response as JSON")
                analysis = {
                    "error": "Failed to parse analysis",
                    "raw_response": analysis_text[:500]  # Truncate long response
                }
                
            return analysis
            
        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            return {"error": f"Analysis failed: {str(e)}"}
    
    def extract_keywords(self, text: str, model: str = "gpt-3.5-turbo") -> List[str]:
        """
        Extract relevant keywords from text.
        
        Args:
            text: The text to analyze
            model: The model to use for keyword extraction
            
        Returns:
            List of keywords
        """
        if not self.api_key or not text:
            return []
            
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Extract the most important keywords from the following text. Return ONLY a JSON array of strings with no additional text."},
                    {"role": "user", "content": text}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse keywords from response
            keywords_text = response.choices[0].message.content
            try:
                keywords_data = json.loads(keywords_text)
                # Handle different possible formats in the response
                if isinstance(keywords_data, list):
                    return keywords_data
                elif "keywords" in keywords_data:
                    return keywords_data.get("keywords", [])
                else:
                    # Try to find any array in the response
                    for key, value in keywords_data.items():
                        if isinstance(value, list):
                            return value
                    return []
            except:
                return []
            
        except Exception as e:
            logger.error(f"Keyword extraction error: {str(e)}")
            return []