"""
Analysis Service
Handles interview transcript analysis using OpenAI LLM with comprehensive evaluation
"""
import logging
import json
from openai import OpenAI
from typing import Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database.models import Recording, Question, CandidateSession
from .report_generator import report_generator

# Configure logging
logger = logging.getLogger(__name__)

class AnalysisService:
    """
    Service for analyzing interview transcripts using OpenAI LLM with comprehensive evaluation.
    """
    def __init__(self):
        """Initialize the analysis service with OpenAI client."""
        if not settings.OPENAI_API_KEY:
            logger.warning("OpenAI API key not found. Analysis service will not be available.")
            self.client = None
        else:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Token usage tracking
        self.token_usage = {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "api_calls": 0
        }

    async def analyze_session_transcripts(self, session_id: int, db: Session) -> Dict[str, Any]:
        """
        Analyze all transcripts for a session using OpenAI with comprehensive evaluation.
        
        Args:
            session_id: Session ID
            db: Database session
            
        Returns:
            Comprehensive analysis results with structured scoring
        """
        if not settings.OPENAI_API_KEY:
            logger.error("OpenAI API key not configured")
            return {"error": "Analysis service not configured"}

        try:
            # Get session info
            session = db.query(CandidateSession).filter(CandidateSession.id == session_id).first()
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            # Get all completed transcriptions for the session
            recordings = db.query(Recording).filter(
                Recording.session_id == session_id,
                Recording.transcription_status == "completed",
                Recording.transcript.isnot(None)
            ).all()
            
            if not recordings:
                raise ValueError(f"No completed transcriptions found for session {session_id}")
            
            # Prepare transcript data with questions and timing analysis
            transcript_data = []
            total_words = 0
            total_speaking_time = 0
            
            for recording in recordings:
                question = db.query(Question).filter(Question.id == recording.question_id).first()
                transcript_json = json.loads(recording.transcript)
                
                # Calculate speaking metrics
                text = transcript_json["text"]
                word_count = len(text.split()) if text else 0
                duration = transcript_json.get("duration", 0)
                
                # Extract pause analysis from segments if available
                segments = transcript_json.get("segments", [])
                pause_analysis = self._analyze_speech_timing(segments) if segments else {}
                
                transcript_data.append({
                    "question_id": recording.question_id,
                    "question_text": question.text if question else "Unknown question",
                    "question_category": getattr(question, 'category', 'general') if question else 'general',
                    "transcript": text,
                    "word_count": word_count,
                    "duration": duration,
                    "speaking_rate": (word_count / (duration / 60)) if duration > 0 else 0,  # words per minute
                    "segments": segments,
                    "pause_analysis": pause_analysis,
                    "recording_id": recording.id
                })
                
                total_words += word_count
                total_speaking_time += duration
            
            # Calculate session-level metrics
            session_metrics = {
                "total_questions": len(transcript_data),
                "total_words": total_words,
                "total_duration": total_speaking_time,
                "average_speaking_rate": (total_words / (total_speaking_time / 60)) if total_speaking_time > 0 else 0,
                "average_response_length": total_words / len(transcript_data) if transcript_data else 0
            }
              # Prepare comprehensive OpenAI prompt
            analysis_prompt = self._build_comprehensive_analysis_prompt(transcript_data, session, session_metrics)
            
            # Call OpenAI API with structured request
            logger.info(f"Starting comprehensive OpenAI analysis for session {session_id} with {len(transcript_data)} responses")
            
            if not self.client:
                raise ValueError("OpenAI client not initialized - API key required")
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use cost-effective model
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                temperature=0.2,  # Lower temperature for more consistent analysis
                max_tokens=4000,  # Reduced to comply with model limits
                response_format={"type": "json_object"}  # Request structured JSON response
            )
            
            # Track token usage
            token_usage = self._track_token_usage(response)
            
            # Parse structured analysis
            try:
                structured_analysis = json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                # Fallback to plain text if JSON parsing fails
                structured_analysis = {
                    "overall_assessment": response.choices[0].message.content,
                    "scores": {},
                    "parsing_error": True
                }
            
            # Build comprehensive analysis result
            analysis_result = {
                "session_id": session_id,
                "candidate_id": session.candidate_id,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
                "session_metrics": session_metrics,
                "structured_analysis": structured_analysis,
                "question_responses": transcript_data,
                "recommendations": {
                    "hiring_recommendation": structured_analysis.get("hiring_recommendation", "requires_review"),
                    "confidence_level": structured_analysis.get("confidence_level", "medium"),
                    "key_strengths": structured_analysis.get("key_strengths", []),
                    "areas_for_improvement": structured_analysis.get("areas_for_improvement", []),
                    "follow_up_questions": structured_analysis.get("follow_up_questions", [])
                },
                "analysis_metadata": {
                    "model_used": response.model,
                    "openai_usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                        "estimated_cost": self._calculate_cost(response.usage, response.model)
                    },
                    "analysis_version": "2.0",
                    "features_used": ["timing_analysis", "structured_scoring", "hiring_recommendation"]
                }
            }
              # Save comprehensive analysis to session
            session.analysis_result = json.dumps(analysis_result)
            session.analysis_status = "completed"
            session.analyzed_at = datetime.now(timezone.utc)
            
            # Add analysis summary to session for quick access
            if isinstance(structured_analysis, dict) and "overall_score" in structured_analysis:
                session.analysis_score = structured_analysis.get("overall_score", 0)
                session.hiring_recommendation = structured_analysis.get("hiring_recommendation", "requires_review")
            
            db.commit()
            
            # Generate visual report using the report generator (free - no additional API calls)
            try:
                logger.info("Generating visual charts for analysis report...")
                visual_report = report_generator.generate_comprehensive_report(analysis_result)
                analysis_result["visual_report"] = visual_report
                logger.info(f"Generated visual report with {visual_report.get('charts_count', 0)} charts")
            except Exception as chart_error:
                logger.warning(f"Visual report generation failed: {str(chart_error)}")
                analysis_result["visual_report"] = {"error": str(chart_error), "charts": {}}
            
            logger.info(f"Comprehensive analysis completed for session {session_id}. "
                       f"Score: {structured_analysis.get('overall_score', 'N/A')}, "
                       f"Recommendation: {structured_analysis.get('hiring_recommendation', 'N/A')}")
            
            return analysis_result
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Analysis failed for session {session_id}: {error_message}")
            
            # Update session with error
            if 'session' in locals() and session:
                session.analysis_status = "failed"
                session.analysis_error = error_message[:500]
                db.commit()            
            raise
    
    def _prepare_combined_transcript(self, recordings: List[Recording], questions: Dict[int, str]) -> str:
        """Prepare combined transcript with questions and responses."""
        transcript_parts = []
        
        for i, recording in enumerate(recordings, 1):
            question_text = questions.get(recording.question_id, f"Question {recording.question_id}")
            transcript_parts.append(f"Question {i}: {question_text}")
            transcript_parts.append(f"Response {i}: {recording.transcript}")
            transcript_parts.append("---")
        
        return "\n\n".join(transcript_parts)
    
    async def _analyze_with_openai(self, combined_transcript: str) -> Dict[str, Any]:
        """Analyze combined transcript using OpenAI."""
        system_message = """
You are an expert interview evaluator. Analyze this complete interview session with multiple questions and responses.

Provide a comprehensive analysis in JSON format with:
{
    "overall_performance": {
        "score": <1-10>,
        "assessment": "Excellent|Good|Average|Poor",
        "summary": "Overall impression..."
    },
    "communication_skills": {
        "score": <1-10>,
        "clarity": "Assessment of clarity",
        "articulation": "Assessment of articulation"
    },
    "technical_competency": {
        "score": <1-10>,
        "depth": "Assessment of technical depth",
        "accuracy": "Assessment of technical accuracy"
    },
    "problem_solving": {
        "score": <1-10>,
        "approach": "Assessment of problem-solving approach",
        "creativity": "Assessment of creative thinking"
    },
    "question_responses": [
        {
            "question_number": 1,
            "score": <1-10>,
            "strengths": ["strength1", "strength2"],
            "areas_for_improvement": ["area1", "area2"]
        }
    ],
    "key_insights": ["insight1", "insight2"],
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "recommendations": ["recommendation1", "recommendation2"]
}
"""
        
        try:
            if not self.client:
                raise ValueError("OpenAI client not initialized - API key required")
            
            response = self.client.chat.completions.create(
                model="gpt-4",  # Use GPT-4 for better analysis
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Interview Transcript:\n\n{combined_transcript}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            # Track token usage
            self._track_token_usage(response)
            
            analysis_text = response.choices[0].message.content
            return json.loads(analysis_text)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
            return {"error": "Failed to parse analysis response"}
        except Exception as e:
            logger.error(f"OpenAI analysis error: {e}")
            return {"error": f"Analysis service error: {str(e)}"}
    
    async def batch_analyze_session(self, session_id: int, db: Session, force_reanalyze: bool = False) -> Dict[str, Any]:
        """
        Batch analyze all transcripts for a session.
        
        Args:
            session_id: Session ID to process
            db: Database session
            force_reanalyze: Re-analyze even if analysis exists
            
        Returns:
            Analysis results
        """
        logger.info(f"Starting batch analysis for session {session_id}")
        
        # Check if we should proceed with analysis
        if not force_reanalyze:
            # Check if analysis already exists
            existing_analysis = db.query(Recording).filter(
                Recording.session_id == session_id,
                Recording.analysis.isnot(None)
            ).first()
            
            if existing_analysis:
                logger.info(f"Analysis already exists for session {session_id}")
                return {"message": "Analysis already completed", "reanalyzed": False}
        
        # Perform analysis
        analysis_result = await self.analyze_session_transcripts(session_id, db)
        
        return {
            "message": "Session analysis completed",
            "analysis_result": analysis_result,
            "reanalyzed": force_reanalyze
        }

    def _analyze_speech_timing(self, segments: List[Dict]) -> Dict[str, Any]:
        """Analyze speech timing patterns from Whisper segments."""
        if not segments:
            return {}
        
        try:
            pauses = []
            speaking_durations = []
            
            for i, segment in enumerate(segments):
                # Calculate speaking duration for this segment
                start = segment.get('start', 0)
                end = segment.get('end', start)
                speaking_duration = end - start
                speaking_durations.append(speaking_duration)
                
                # Calculate pause before next segment
                if i < len(segments) - 1:
                    next_start = segments[i + 1].get('start', end)
                    pause_duration = next_start - end
                    if pause_duration > 0.1:  # Only count pauses > 100ms
                        pauses.append(pause_duration)
            
            return {
                "total_pauses": len(pauses),
                "average_pause_duration": sum(pauses) / len(pauses) if pauses else 0,
                "longest_pause": max(pauses) if pauses else 0,
                "speaking_segments": len(speaking_durations),
                "average_segment_duration": sum(speaking_durations) / len(speaking_durations) if speaking_durations else 0,
                "speech_continuity_score": self._calculate_continuity_score(pauses, speaking_durations)
            }
        except Exception as e:
            logger.warning(f"Error analyzing speech timing: {str(e)}")
            return {"error": "timing_analysis_failed"}

    def _calculate_continuity_score(self, pauses: List[float], speaking_durations: List[float]) -> float:
        """Calculate a speech continuity score (0-10)."""
        if not speaking_durations:
            return 0
        
        total_speaking_time = sum(speaking_durations)
        total_pause_time = sum(pauses)
        
        if total_speaking_time + total_pause_time == 0:
            return 5  # neutral score
        
        # Score based on ratio of speaking to total time
        continuity_ratio = total_speaking_time / (total_speaking_time + total_pause_time)
        
        # Penalize excessive long pauses
        long_pause_penalty = sum(1 for pause in pauses if pause > 3.0) * 0.5
        
        score = (continuity_ratio * 10) - long_pause_penalty
        return max(0, min(10, score))

    def _build_comprehensive_analysis_prompt(self, transcript_data: List[Dict], session, session_metrics: Dict) -> str:
        """Build comprehensive analysis prompt with structured output request."""
        prompt = f"""
Analyze this video interview session comprehensively. Provide your response as a valid JSON object.

## Interview Context
- Session ID: {session.id}
- Candidate ID: {session.candidate_id}
- Total Questions: {session_metrics['total_questions']}
- Total Speaking Time: {session_metrics['total_duration']:.1f} seconds
- Total Words: {session_metrics['total_words']}
- Average Speaking Rate: {session_metrics['average_speaking_rate']:.1f} words/minute

## Questions and Detailed Responses
"""
        
        for i, data in enumerate(transcript_data, 1):
            prompt += f"""
### Question {i} [{data.get('question_category', 'general').upper()}]
**Question:** {data['question_text']}
**Response:** {data['transcript']}
**Metrics:** {data['word_count']} words, {data['duration']:.1f}s, {data['speaking_rate']:.1f} wpm
"""
            if data.get('pause_analysis'):
                pause_info = data['pause_analysis']
                prompt += f"**Speech Pattern:** {pause_info.get('total_pauses', 0)} pauses, continuity score {pause_info.get('speech_continuity_score', 0):.1f}/10\n"
            prompt += "\n"
        
        prompt += """
## Required JSON Response Format
Provide your analysis as a JSON object with this exact structure:

{
  "overall_score": <number 1-10>,
  "hiring_recommendation": "<hire|no_hire|requires_review>",
  "confidence_level": "<low|medium|high>",
  "scores": {
    "communication_skills": <number 1-10>,
    "technical_knowledge": <number 1-10>,
    "problem_solving": <number 1-10>,
    "cultural_fit": <number 1-10>,
    "experience_relevance": <number 1-10>
  },
  "assessment": {
    "strengths": ["<strength 1>", "<strength 2>", "..."],
    "weaknesses": ["<weakness 1>", "<weakness 2>", "..."],
    "communication_quality": "<excellent|good|fair|poor>",
    "response_depth": "<excellent|good|fair|poor>",
    "technical_accuracy": "<excellent|good|fair|poor>"
  },
  "key_insights": [
    "<insight 1>",
    "<insight 2>",
    "..."
  ],
  "evidence_examples": [
    {
      "question_number": <number>,
      "observation": "<what you observed>",
      "evidence": "<specific quote or behavior>",
      "impact": "<positive|negative|neutral>"
    }
  ],
  "recommendations": {
    "next_steps": "<detailed recommendation>",
    "focus_areas": ["<area 1>", "<area 2>", "..."],
    "additional_evaluation": "<yes|no>",
    "role_suitability": "<high|medium|low>"
  },
  "follow_up_questions": [
    "<question 1>",
    "<question 2>",
    "..."
  ]
}

## Analysis Guidelines
1. Be objective and evidence-based
2. Quote specific examples from responses
3. Consider both verbal content and communication patterns
4. Evaluate technical accuracy where applicable
5. Assess soft skills and cultural fit indicators
6. Provide actionable insights for hiring decisions
7. Consider the speaking patterns and fluency metrics provided
"""
        
        return prompt

    def _get_system_prompt(self) -> str:
        """Get the system prompt for OpenAI analysis."""
        return """You are an expert interview analyst specializing in comprehensive candidate evaluation. 

Your role is to:
- Analyze video interview responses objectively and thoroughly
- Provide structured, evidence-based assessments
- Score candidates across multiple dimensions
- Make clear hiring recommendations with supporting evidence
- Identify specific strengths, weaknesses, and development areas
- Consider both technical competence and soft skills
- Factor in communication patterns and speaking fluency

Always respond with valid JSON in the exact format requested. Be thorough but concise in your analysis."""

    def _calculate_cost(self, usage, model: str) -> float:
        """Calculate estimated OpenAI API cost."""
        # Pricing as of 2024 (per 1K tokens)
        pricing = {
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},  # Much cheaper!
            "gpt-4-1106-preview": {"input": 0.01, "output": 0.03},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002}
        }
        
        model_pricing = pricing.get(model, pricing["gpt-4o-mini"])
        
        input_cost = (usage.prompt_tokens / 1000) * model_pricing["input"]
        output_cost = (usage.completion_tokens / 1000) * model_pricing["output"]
        
        return round(input_cost + output_cost, 6)

    def _track_token_usage(self, response) -> Dict[str, int]:
        """Track token usage from OpenAI API response."""
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,  
                "total_tokens": response.usage.total_tokens
            }
            
            # Update running totals
            self.token_usage["total_prompt_tokens"] += usage["prompt_tokens"]
            self.token_usage["total_completion_tokens"] += usage["completion_tokens"]
            self.token_usage["total_tokens"] += usage["total_tokens"]
            self.token_usage["api_calls"] += 1
            
            logger.info(f"Token usage - Prompt: {usage['prompt_tokens']}, "
                       f"Completion: {usage['completion_tokens']}, "
                       f"Total: {usage['total_tokens']}")
            
            return usage
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def get_token_usage_summary(self) -> Dict[str, int]:
        """Get summary of token usage for this session."""
        return self.token_usage.copy()

    def reset_token_usage(self):
        """Reset token usage counters."""
        self.token_usage = {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "api_calls": 0
        }


# Create singleton instance
analysis_service = AnalysisService()