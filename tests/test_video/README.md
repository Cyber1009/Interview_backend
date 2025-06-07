# Test Video Directory

This directory contains test files for the interview session flow test.

## Files Structure

- **Video Files**: `A1.mp4`, `A2.mp4`, `A3.mp4`, `A4.mp4` - Answer-only video recordings
- **Questions File**: `QUESTIONS.txt` - Questions corresponding to each video
- **backup/**: Backup directory for test files

## Questions File Format

The `questions.txt` file should follow this format (note: filename updated to lowercase):

```
Q1: First question text here
Q2: Second question text here  
Q3: Third question text here
Q4: Fourth question text here
```

### Format Rules:
1. Each line starts with `Q` followed by a number and colon (e.g., `Q1:`)
2. The question text follows after the colon and space
3. Questions are numbered sequentially (Q1, Q2, Q3, etc.)
4. The number of questions should match the number of video files
5. UTF-8 encoding is supported for international characters

### Test Auto-Discovery:
- The test automatically discovers video files (.mp4, .avi, .mov, .mkv, .webm)
- Loads questions from `questions.txt` using Q1:/Q2: format
- Matches videos to questions by number (A1.mp4 → Q1, A2.mp4 → Q2, etc.)
- Falls back to default questions if questions.txt fails to load

Q4: Fourth question text here?
```

### Format Rules:
- Each question starts with `Q<number>:` (e.g., `Q1:`, `Q2:`)
- Questions can span multiple lines
- Blank lines between questions are optional
- The test will auto-match questions to videos (Q1 → A1.mp4, Q2 → A2.mp4, etc.)

## Test Usage

The test system will:
1. Auto-discover all video files in this directory (supports .mp4, .avi, .mov, .mkv, .webm)
2. Load questions from `QUESTIONS.txt` using the Q1:/Q2: format
3. Transcribe each video separately (simulating async processing)
4. Analyze all transcripts together in a single comprehensive analysis

## Running Tests

```bash
# Run the specific test
python -m pytest tests/test_session_flow_new.py::test_interview_session_flow -v -s

# Or run the test directly
python tests/test_session_flow_new.py
```

## Expected Output

The test will generate:
- Transcription results for each video
- Comprehensive analysis with hiring recommendations
- Token usage statistics
- Results saved to `test_results/` directory
