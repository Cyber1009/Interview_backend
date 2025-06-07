"""
Test for interview session flow using existing transcription and analysis services.
Tests the actual app flow: transcribe answer-only videos separately → analyze all transcripts together.

This test:
1. Uses TranscriptionService.transcribe_file() to transcribe each answer video separately (simulating async)
2. Loads actual questions from questions.txt file in the test directory
3. Creates mock database session with recordings and questions
4. Uses AnalysisService.analyze_session_transcripts() to analyze all transcripts together in one LLM call
5. Tests with video files found in tests/test_video/ directory as a single candidate session
"""
import os
import sys
import logging
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.transcription.transcription_service import TranscriptionService
from app.services.analysis.analysis_service import AnalysisService
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InterviewSessionFlowTest:
    """Test that follows the actual app flow: separate transcription → combined analysis."""
    
    def __init__(self):
        """Initialize with existing services."""
        self.transcription_service = TranscriptionService()
        self.analysis_service = AnalysisService()
        
        # Use tests/test_video directory for test files
        self.test_videos_path = Path(__file__).parent / "test_video"
        self.questions_file = self.test_videos_path / "questions.txt"
        
        # Automatically discover video files in test directory
        self.test_videos = self._discover_video_files()
        
        # Load actual questions from questions.txt file
        self.questions = self._load_questions_from_file()
        
    def _discover_video_files(self) -> List[str]:
        """Automatically discover video files in the test directory."""
        if not self.test_videos_path.exists():
            raise FileNotFoundError(f"Test video directory not found: {self.test_videos_path}")
        
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend([f.name for f in self.test_videos_path.glob(f"*{ext}")])
        
        if not video_files:
            raise FileNotFoundError(f"No video files found in {self.test_videos_path}")
        
        # Sort files naturally (A1.mp4, A2.mp4, etc.)
        video_files.sort()
        logger.info(f"Discovered {len(video_files)} video files: {video_files}")
        return video_files
        
    def _load_questions_from_file(self) -> List[str]:
        """Load questions from questions.txt file in the test directory."""
        if not self.questions_file.exists():
            raise FileNotFoundError(f"Questions file not found: {self.questions_file}")
        
        questions = []
        
        try:
            with open(self.questions_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse questions from the file
            lines = content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('Q') and ':' in line:
                    # Extract question text after "Q1:", "Q2:", etc.
                    question_text = line.split(':', 1)[1].strip()
                    questions.append(question_text)
            
            logger.info(f"Loaded {len(questions)} questions from questions.txt")
            return questions
            
        except Exception as e:
            logger.error(f"Failed to load questions from file: {str(e)}")
            # Fallback to default questions if file reading fails
            return [
                "Would you be interested in upgrading the skills you currently have as they relate to the programs mentioned in our job ad?",
                "Do you find that working with others comes easily to you or do you prefer to work on your own?",
                "And would you say that you've taken the lead on team projects in the past? If so, could you provide us with a few examples?",
                "So those are the main questions that we have for you, but do you have any questions for us?"
            ]
    
    def _verify_test_files(self) -> bool:
        """Verify all test video files exist."""
        logger.info("Verifying test video files...")
        
        if not self.test_videos_path.exists():
            logger.error(f"Test videos directory not found: {self.test_videos_path}")
            return False
        
        missing_files = []
        for video in self.test_videos:
            video_path = self.test_videos_path / video
            if not video_path.exists():
                missing_files.append(str(video_path))
        
        if missing_files:
            logger.error(f"Missing test video files: {missing_files}")
            return False
        
        logger.info("✅ All test video files found!")
        return True
    
    def transcribe_videos_separately(self) -> List[Dict[str, Any]]:
        """
        Step 1: Transcribe each video separately (simulating async behavior).
        This matches the app flow where videos are uploaded and transcribed individually.
        """
        logger.info("🎙️ Starting individual video transcription...")
        transcripts = []
        
        for i, video_file in enumerate(self.test_videos, 1):
            video_path = self.test_videos_path / video_file
            logger.info(f"Transcribing {video_file} (Question {i})...")
            
            try:
                # Use existing transcription service
                result = self.transcription_service.transcribe_file(str(video_path))
                
                if "error" in result:
                    logger.error(f"❌ Transcription failed for {video_file}: {result['error']}")
                    transcripts.append({
                        "question_id": i,
                        "video_file": video_file,
                        "error": result["error"]
                    })
                else:
                    logger.info(f"✅ Successfully transcribed {video_file}")
                    transcripts.append({
                        "question_id": i,
                        "question_text": self.questions[i-1] if i <= len(self.questions) else f"Question {i}",
                        "video_file": video_file,
                        "transcript": result["text"],
                        "language": result.get("language", "unknown"),
                        "duration": result.get("duration", 0),
                        "segments": result.get("segments", []),
                        "word_count": len(result["text"].split()) if result.get("text") else 0
                    })
                    
            except Exception as e:
                logger.error(f"❌ Exception during transcription of {video_file}: {str(e)}")
                transcripts.append({
                    "question_id": i,
                    "video_file": video_file,
                    "error": f"Exception: {str(e)}"
                })
        
        successful_transcripts = [t for t in transcripts if "error" not in t]
        logger.info(f"📝 Transcription completed: {len(successful_transcripts)}/{len(self.test_videos)} successful")
        
        return transcripts
    
    def create_mock_database_session(self, transcripts: List[Dict[str, Any]]) -> Mock:
        """
        Create mock database session with recordings and questions.
        This simulates the database state after videos are transcribed.
        """
        logger.info("🗄️ Creating mock database session...")
        
        # Create mock objects
        mock_db = Mock()
        mock_session = Mock()
        mock_questions = []
        mock_recordings = []
        
        # Create mock questions
        for i, question_text in enumerate(self.questions, 1):
            mock_question = Mock()
            mock_question.id = i
            mock_question.text = question_text
            mock_question.category = "general"
            mock_questions.append(mock_question)
        
        # Create mock recordings with transcripts
        for transcript_data in transcripts:
            if "error" not in transcript_data:
                mock_recording = Mock()
                mock_recording.id = transcript_data["question_id"]
                mock_recording.session_id = 1  # Single test session
                mock_recording.question_id = transcript_data["question_id"]
                mock_recording.transcription_status = "completed"
                
                # Format transcript data as JSON (as stored in database)
                transcript_json = {
                    "text": transcript_data["transcript"],
                    "language": transcript_data["language"],
                    "duration": transcript_data["duration"],
                    "segments": transcript_data["segments"]
                }
                mock_recording.transcript = json.dumps(transcript_json)
                mock_recordings.append(mock_recording)
        
        # Mock session
        mock_session.id = 1
        mock_session.candidate_id = "test_candidate_001"
        
        # Configure mock database queries
        def mock_query(model):
            query_mock = Mock()
            if model.__name__ == "CandidateSession":
                query_mock.filter.return_value.first.return_value = mock_session
            elif model.__name__ == "Recording":
                filtered_mock = Mock()
                filtered_mock.all.return_value = mock_recordings
                query_mock.filter.return_value = filtered_mock
            elif model.__name__ == "Question":
                def question_filter(*args):
                    question_id = args[0].right.value if hasattr(args[0], 'right') else 1
                    matching_question = next((q for q in mock_questions if q.id == question_id), mock_questions[0])
                    filter_mock = Mock()
                    filter_mock.first.return_value = matching_question
                    return filter_mock
                query_mock.filter = question_filter
            return query_mock
        
        mock_db.query = mock_query
        
        logger.info(f"✅ Mock database created with {len(mock_recordings)} recordings and {len(mock_questions)} questions")
        return mock_db
    
    def analyze_session_transcripts(self, mock_db: Mock) -> Dict[str, Any]:
        """
        Step 2: Analyze all transcripts together using the existing analysis service.
        This matches the app flow where all transcripts are analyzed in a single LLM call.
        """
        logger.info("🧠 Starting comprehensive session analysis...")
        
        try:
            # Use existing analysis service with mock database
            result = asyncio.run(self.analysis_service.analyze_session_transcripts(
                session_id=1, 
                db=mock_db
            ))
            
            if "error" in result:
                logger.error(f"❌ Analysis failed: {result['error']}")
                return result
            else:
                logger.info("✅ Session analysis completed successfully!")
                return result
                
        except Exception as e:
            logger.error(f"❌ Exception during analysis: {str(e)}")
            return {"error": f"Analysis exception: {str(e)}"}
    def save_results(self, transcripts: List[Dict[str, Any]], analysis_result: Dict[str, Any]):
        """Save test results to files."""
        output_dir = Path(__file__).parent / "test_results"
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save individual transcripts
        transcripts_file = output_dir / f"session_flow_transcripts_{timestamp}.json"
        with open(transcripts_file, 'w', encoding='utf-8') as f:
            json.dump(transcripts, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Saved transcripts to {transcripts_file}")
        
        # Save analysis results
        analysis_file = output_dir / f"session_flow_analysis_{timestamp}.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Saved analysis to {analysis_file}")
        
        # Create summary report
        summary_file = output_dir / f"session_flow_summary_{timestamp}.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("INTERVIEW SESSION FLOW TEST RESULTS\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Videos Processed: {len(self.test_videos)}\n")
            
            successful_transcripts = [t for t in transcripts if "error" not in t]
            f.write(f"Successful Transcriptions: {len(successful_transcripts)}/{len(transcripts)}\n\n")
            
            if "error" not in analysis_result:
                f.write("ANALYSIS SUCCESS!\n")
                f.write(f"Session ID: {analysis_result.get('session_id', 'N/A')}\n")
                f.write(f"Analysis completed at: {analysis_result.get('analyzed_at', 'N/A')}\n")
                
                # Show session metrics if available
                if 'session_metrics' in analysis_result:
                    metrics = analysis_result['session_metrics']
                    f.write(f"Total Words: {metrics.get('total_words', 'N/A')}\n")
                    f.write(f"Total Duration: {metrics.get('total_duration', 'N/A')} seconds\n")
                    f.write(f"Average Speaking Rate: {metrics.get('average_speaking_rate', 'N/A')} words/min\n")
                
                # Show recommendations if available
                if 'recommendations' in analysis_result:
                    recs = analysis_result['recommendations']
                    f.write(f"Hiring Recommendation: {recs.get('hiring_recommendation', 'N/A')}\n")
                    f.write(f"Confidence Level: {recs.get('confidence_level', 'N/A')}\n")
            else:
                f.write(f"ANALYSIS FAILED: {analysis_result['error']}\n")
        
        logger.info(f"💾 Saved summary to {summary_file}")
    
    def print_summary(self, transcripts: List[Dict[str, Any]], analysis_result: Dict[str, Any]):
        """Print test results summary."""
        print("\n" + "="*80)
        print("🎯 INTERVIEW SESSION FLOW TEST RESULTS")
        print("="*80)
        
        # Transcription results
        print(f"\n📝 TRANSCRIPTION RESULTS:")
        print("-" * 50)
        successful_transcripts = [t for t in transcripts if "error" not in t]
        print(f"   Videos Processed: {len(self.test_videos)}")
        print(f"   Successful: {len(successful_transcripts)}")
        print(f"   Failed: {len(transcripts) - len(successful_transcripts)}")
        
        for transcript in transcripts:
            if "error" not in transcript:
                print(f"   ✅ {transcript['video_file']}: {transcript['word_count']} words, {transcript['duration']:.1f}s")
            else:
                print(f"   ❌ {transcript['video_file']}: {transcript['error']}")
          # Analysis results
        print(f"\n🧠 ANALYSIS RESULTS:")
        print("-" * 50)
        if "error" not in analysis_result:
            print("   ✅ Session analysis completed successfully!")
            
            if 'session_metrics' in analysis_result:
                metrics = analysis_result['session_metrics']
                print(f"   Total Questions: {metrics.get('total_questions', 'N/A')}")
                print(f"   Total Words: {metrics.get('total_words', 'N/A')}")
                print(f"   Total Duration: {metrics.get('total_duration', 0):.1f} seconds")
                print(f"   Average Speaking Rate: {metrics.get('average_speaking_rate', 0):.1f} words/min")
            
            if 'recommendations' in analysis_result:
                recs = analysis_result['recommendations']
                print(f"   Hiring Recommendation: {recs.get('hiring_recommendation', 'N/A')}")
                print(f"   Confidence Level: {recs.get('confidence_level', 'N/A')}")
                
                strengths = recs.get('key_strengths', [])
                if strengths:
                    print(f"   Key Strengths: {', '.join(strengths[:3])}")
                
                improvements = recs.get('areas_for_improvement', [])
                if improvements:
                    print(f"   Areas for Improvement: {', '.join(improvements[:3])}")
                    
            # Token usage information
            if 'analysis_metadata' in analysis_result and 'openai_usage' in analysis_result['analysis_metadata']:
                usage = analysis_result['analysis_metadata']['openai_usage']
                print(f"\n💰 TOKEN USAGE:")
                print(f"   Prompt Tokens: {usage.get('prompt_tokens', 'N/A')}")
                print(f"   Completion Tokens: {usage.get('completion_tokens', 'N/A')}")
                print(f"   Total Tokens: {usage.get('total_tokens', 'N/A')}")
                print(f"   Estimated Cost: ${usage.get('estimated_cost', 'N/A')}")
                
        else:
            print(f"   ❌ Analysis failed: {analysis_result['error']}")
        
        print("\n" + "="*80)
    
    def print_token_usage_summary(self):
        """Print overall token usage summary from the analysis service."""
        if hasattr(self.analysis_service, 'get_token_usage_summary'):
            usage_summary = self.analysis_service.get_token_usage_summary()
            if usage_summary['api_calls'] > 0:
                print(f"\n📊 OVERALL TOKEN USAGE SUMMARY:")
                print("-" * 50)
                print(f"   Total API Calls: {usage_summary['api_calls']}")
                print(f"   Total Prompt Tokens: {usage_summary['total_prompt_tokens']}")
                print(f"   Total Completion Tokens: {usage_summary['total_completion_tokens']}")
                print(f"   Total Tokens Used: {usage_summary['total_tokens']}")
                
                # Calculate estimated total cost (rough estimate)
                avg_cost_per_1k = 0.02  # Average cost per 1K tokens
                estimated_total_cost = (usage_summary['total_tokens'] / 1000) * avg_cost_per_1k
                print(f"   Estimated Total Cost: ${estimated_total_cost:.4f}")
    
    def run_test(self) -> bool:
        """
        Run the complete interview session flow test.
        
        Returns:
            bool: True if test completed successfully
        """
        logger.info("🚀 Starting Interview Session Flow Test")
        
        # Verify files exist
        if not self._verify_test_files():
            return False
        
        try:
            # Step 1: Transcribe videos separately (simulating async uploads)
            transcripts = self.transcribe_videos_separately()
            
            # Check if we have any successful transcripts
            successful_transcripts = [t for t in transcripts if "error" not in t]
            if not successful_transcripts:
                logger.error("❌ No successful transcriptions - cannot proceed with analysis")
                return False
            
            # Step 2: Create mock database session
            mock_db = self.create_mock_database_session(transcripts)
            
            # Step 3: Analyze all transcripts together
            analysis_result = self.analyze_session_transcripts(mock_db)
              # Step 4: Save and display results
            self.save_results(transcripts, analysis_result)
            self.print_summary(transcripts, analysis_result)
            
            # Display overall token usage
            self.print_token_usage_summary()
            
            success = "error" not in analysis_result
            if success:
                logger.info("✅ Interview session flow test completed successfully!")
            else:
                logger.error("❌ Test completed but analysis failed")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Test failed with exception: {str(e)}")
            return False


def main():
    """Main function to run the test."""
    
    # Check API key
    if not settings.OPENAI_API_KEY:
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("This test requires OpenAI API key for analysis")
        return
    
    print("🎯 Interview Session Flow Test")
    print("=" * 50)
    print(f"📁 Test videos: tests/test_video/ (auto-discovered)")
    print(f"📄 Questions: tests/test_video/questions.txt") 
    print(f"🔑 OpenAI API: {'✅ Available' if settings.OPENAI_API_KEY else '❌ Missing'}")
    print(f"🎤 Transcription: Local Whisper (via TranscriptionService)")
    print(f"🧠 Analysis: OpenAI LLM (via AnalysisService)")
    print(f"🔄 Flow: Answer-only videos → Separate transcription → Combined analysis")
    print()
    
    # Run test
    test = InterviewSessionFlowTest()
    success = test.run_test()
    if success:
        print(f"\n📄 Results saved to: tests/test_results/")
        print("💡 This test validates the actual app flow used in production")
    
    return success

def test_interview_session_flow():
    """Pytest test function for interview session flow."""
    # Check API key
    if not settings.OPENAI_API_KEY:
        logger.warning("⚠️ OPENAI_API_KEY not found - skipping test")
        import pytest
        pytest.skip("OpenAI API key required for this test")
    
    # Run the test
    test = InterviewSessionFlowTest()
    success = test.run_test()
    
    # Assert the test passed
    assert success, "Interview session flow test failed"


if __name__ == "__main__":
    main()
