# Video Analysis Pipeline Test

This test script (`test_video_analysis_pipeline.py`) provides a comprehensive test of the complete video analysis pipeline:

## What it tests:
1. **Video File Discovery** - Finds video/audio files in test directories
2. **Transcription Service** - Tests local Whisper transcription
3. **Content Analysis** - Tests hiring-focused analysis using ContentAnalysisService
4. **Comprehensive Analysis** - Tests full interview analysis using InterviewAnalysisService
5. **Integrated Pipeline** - Tests the complete pipeline using IntegratedInterviewService

## Supported file formats:
- Video: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.flv`
- Audio: `.wav`, `.mp3`, `.m4a`

## Test locations searched:
1. `uploads/recordings/test/` (recommended for test files)
2. `uploads/recordings/`
3. `tests/test_files/`
4. `test_files/`
5. Current directory

## How to run:

### Basic run:
```bash
python tests/test_video_analysis_pipeline.py
```

### Requirements:
- **Transcription**: Works with local Whisper (no API key needed)
- **Analysis**: Requires OpenAI API key in environment or config
  - Set `OPENAI_API_KEY` environment variable
  - Or configure in `app/core/config.py`

## Expected output:
- Console output showing progress and results
- Saved files in `test_results/` directory:
  - `{video_name}_analysis_{timestamp}.json` - Complete results
  - `{video_name}_summary_{timestamp}.txt` - Human-readable summary

## Sample test files:
Place test video/audio files in `uploads/recordings/test/` for best results.

## Services tested:
- ✅ **ContentAnalysisService** - Main production analysis service
- ✅ **InterviewAnalysisService** - Comprehensive analysis with speaking patterns
- ✅ **IntegratedInterviewService** - Full pipeline (transcription + analysis)
- ✅ **UnifiedTranscriptionService** - Local Whisper transcription

## Troubleshooting:
- **No video files found**: Add test files to `uploads/recordings/test/`
- **Analysis skipped**: Configure OpenAI API key
- **Transcription fails**: Check Whisper installation (`pip install openai-whisper`)
