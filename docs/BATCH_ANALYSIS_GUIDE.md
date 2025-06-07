# Interview Analysis Service - Batch Analysis Guide

## Overview

The Interview Analysis Service has been optimized to support batch analysis where all question responses are collected first and then analyzed together. This approach provides:

1. **Better Cross-Question Insights**: Analyzes consistency and patterns across all responses
2. **Token Efficiency**: Single API call instead of multiple individual calls  
3. **Comprehensive Assessment**: More accurate overall evaluation based on complete interview data
4. **Preserved Context**: Maintains question-answer relationships for better analysis

## Key Features Implemented

### 1. Batch Collection and Analysis
- **collect_interview_data()**: Initialize a collection session
- **add_response_to_session()**: Add individual responses without immediate analysis
- **analyze_complete_interview()**: Perform comprehensive analysis on all collected data

### 2. Optimized Token Usage
- Reduced segment analysis from 20 to 15 most relevant segments
- Shortened field names in segment data (duration → dur, confidence → conf)
- Truncated long text segments to 100 characters
- Combined multiple analyses into single API calls

### 3. Transcript-Focused Analysis
- Removed audio-only features like "pitch and tone analysis"
- Focus on transcript-based stress indicators (hesitations, fillers, pace variations)
- Authenticity assessment based on content consistency and detail level

### 4. Enhanced Cross-Question Analysis
- **Combined Content Analysis**: Evaluates responses across all questions
- **Combined Stress Analysis**: Identifies stress patterns throughout the interview
- **Combined Authenticity Assessment**: Cross-validates authenticity across responses

## Usage Examples

### Basic Batch Analysis

```python
from app.services.analysis.interview_analysis_service import interview_analysis_service

# 1. Initialize collection session
session = interview_analysis_service.collect_interview_data()

# 2. Add responses as they come in (no analysis yet)
for question, transcription_result in interview_data:
    session = interview_analysis_service.add_response_to_session(
        session, 
        transcription_result, 
        question_text=question
    )

# 3. Perform comprehensive analysis after all questions
context = {
    "role": "Software Engineer", 
    "company": "Tech Corp"
}
final_analysis = interview_analysis_service.analyze_complete_interview(session, context)
```

### Integration with Transcription Service

```python
from app.services.analysis.integrated_interview_service import IntegratedInterviewService

# For processing multiple question recordings
service = IntegratedInterviewService()

# Initialize session
session = service.analysis_service.collect_interview_data()

# Process each question recording
questions = [
    "Tell me about your experience with Python",
    "Describe a challenging project you worked on",
    "How do you handle tight deadlines?"
]

for i, question in enumerate(questions):
    audio_file = f"question_{i+1}.wav"
    
    # Transcribe only
    transcription = service.transcription_service.transcribe_file(audio_file)
    
    # Add to session without analysis
    session = service.analysis_service.add_response_to_session(
        session, 
        transcription, 
        question_text=question
    )

# Analyze complete interview
context = {"role": "Senior Developer", "company": "StartupXYZ"}
complete_analysis = service.analysis_service.analyze_complete_interview(session, context)
```

## API Response Structure

### Session Data Structure
```json
{
    "session_id": "2024-01-15T10:30:00.000Z",
    "collected_responses": [
        {
            "question": "Tell me about your Python experience",
            "text": "I have been working with Python for...",
            "segments": [...],
            "timestamp": "2024-01-15T10:30:15.000Z"
        }
    ],
    "status": "collecting",
    "last_updated": "2024-01-15T10:30:15.000Z"
}
```

### Complete Analysis Response
```json
{
    "status": "completed",
    "timestamp": "2024-01-15T10:35:00.000Z",
    "session_id": "2024-01-15T10:30:00.000Z",
    "total_responses_analyzed": 3,
    "content_analysis": {
        "hiring_recommendation": {
            "decision": "HIRE",
            "confidence_level": "High",
            "key_reasoning": "Strong technical competency..."
        },
        "cross_question_insights": {
            "consistency": "High consistency across responses",
            "authenticity": "Genuine examples with specific details"
        }
    },
    "speaking_analysis": {
        "timing_metrics": {...},
        "confidence_metrics": {...},
        "pattern_analysis": {...}
    },
    "overall_assessment": {
        "final_decision": "HIRE",
        "confidence_level": "High",
        "overall_score": 85,
        "key_strengths": [...],
        "concerns_and_risks": [...]
    }
}
```

## Token Optimization Features

### 1. Efficient Segment Processing
- Analyzes only 15 most meaningful segments
- Filters out very short segments (< 2 words)
- Truncates long text to 100 characters
- Uses shortened field names

### 2. Combined API Calls
- Single call for content analysis across all questions
- Combined stress analysis for pattern detection
- Integrated authenticity assessment

### 3. Focused Prompts
- Concise, targeted prompts for each analysis type
- Reduced max_tokens for responses
- Essential information only

## Migration from Individual Analysis

### Old Approach (Per Question)
```python
# Previous: Analyze each response individually
for transcription_result in results:
    analysis = interview_analysis_service.analyze_interview(transcription_result, context)
    # Process individual analysis
```

### New Approach (Batch)
```python
# New: Collect all, then analyze together
session = interview_analysis_service.collect_interview_data()

for transcription_result in results:
    session = interview_analysis_service.add_response_to_session(session, transcription_result)

# Single comprehensive analysis
complete_analysis = interview_analysis_service.analyze_complete_interview(session, context)
```

## Benefits

1. **Cost Efficiency**: Significant reduction in API token usage
2. **Better Insights**: Cross-question consistency analysis
3. **Improved Accuracy**: More context for assessment decisions
4. **Streamlined Process**: Single analysis result instead of multiple fragments
5. **Enhanced Reporting**: Comprehensive interview overview

## Backward Compatibility

The original `analyze_interview()` method remains available for single-question analysis or legacy integration, but the new batch approach is recommended for multi-question interviews.
