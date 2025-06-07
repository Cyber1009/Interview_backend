# API Consolidation Plan - Updated Status

## Overview
This document outlines the plan to consolidate redundant API endpoints and improve the overall API structure for better clarity and maintainability.

## ✅ COMPLETED: Recording Upload Endpoints 
**RESOLVED**: The duplicate recording upload endpoint in `candidates.py` has already been removed in previous work. Only the token-based endpoint in `recordings.py` remains active.

## 🔄 IN PROGRESS: Recording Retrieval Consolidation


### Current Redundant Recording Retrieval Endpoints:
1. **results.py**: 
   - `/{session_id}/recordings/{recording_id}/download` - File download/streaming
   - `/{session_id}/recordings/{recording_id}` - Recording details with file URL

2. **optimized_results.py**:
   - ~~`/{session_id}/recordings/{recording_id}/data-only`~~ - ✅ REMOVED (redundant)
   - ~~`/recordings/generate-url`~~ - ✅ DEPRECATED (functionality merged)

### Consolidation Strategy:
**IMPLEMENTED**: Enhanced main endpoint with comprehensive query parameters
- `GET /{session_id}/recordings/{recording_id}` with options:
  - `include_file_url=false` - For cost-optimized metadata-only requests
  - `generate_url=true` - For generating fresh S3 URLs
  - `expires_in=3600` - URL expiration time in seconds
  - `inline=true|false` - Whether URL is for inline viewing or download
- Added deprecation notice to the redundant URL generation endpoint

## 🔄 IN PROGRESS: Batch Endpoint Rename

### ✅ COMPLETED: Batch Upload → Analyze Rename  
**RESOLVED**: Successfully renamed `POST /analyze` endpoint in batch.py and fixed syntax errors.

## Phase 2: Session Management Consolidation

### ✅ COMPLETED: Legacy Session Management
**VERIFIED**: Legacy session endpoints have been properly consolidated. Current session management uses the unified approach:
- `POST /api/v1/candidates/interviews/start-session` - For starting a new interview session
- `PATCH /api/v1/candidates/interviews/complete-session` - For completing an interview session
- No legacy `/session` endpoint exists anymore

## ⏳ PLANNED: URL Structure Optimization

### 3.1 Simplified Recording Access
```
# Current (Enhanced but still lengthy)
GET /api/v1/interviewer/interviews/{interview_key}/results/{session_id}/recordings/{recording_id}?include_file_url=false&generate_url=true

# Planned (Future Implementation)
GET /api/v1/interviewer/recordings/{recording_id}?format=metadata|download|stream&session_id={session_id}
```

**Implementation Plan:**
1. Create new router in `api/endpoints/interviewer/recordings.py`
2. Implement the simplified endpoint with format parameter
3. Update authentication flow to verify access rights via session_id
4. Add redirect from old URLs to support backward compatibility
5. Document new URL structure in API docs and examples

**Benefits:**
- 50% shorter URLs for API consumers
- More RESTful resource-based structure
- Clearer parameter naming with format selection
- Better discoverability through consistent pattern

### 3.2 Consistent Resource Naming

**Current State:**
- ✅ All candidate-facing endpoints under `/api/v1/candidates/`
- ✅ All interviewer-facing endpoints under `/api/v1/interviewer/`
- ✅ Batch operations clearly separated with `/batch/` prefix and renamed to `/analyze`

**Planned Improvements:**
- Direct resource paths instead of nested hierarchies:
  - `/api/v1/interviewer/recordings/` instead of `/interviewer/interviews/{id}/results/{id}/recordings/`
  - `/api/v1/interviewer/sessions/` instead of `/interviewer/interviews/{id}/results/`
  - `/api/v1/candidates/interviews/recordings` for all candidate recording uploads

**Implementation Timeline:**
- Phase 1 (Current): Functional consolidation with existing URL structures
- Phase 2 (Q3 2023): URL structure optimization with redirects for backward compatibility
- Phase 3 (Q4 2023): Complete migration to new URL structure

## ⏳ PLANNED: Test Case Implementation

To ensure the consolidated API endpoints work correctly and maintain backward compatibility, the following test cases need to be implemented:

### 1. Recording Retrieval Tests

```python
# Test cases for enhanced recording endpoint
def test_recording_metadata_only():
    # Test retrieving recording without file URL (cost optimization)
    response = client.get(f"/api/v1/interviewer/interviews/{interview_key}/results/{session_id}/recordings/{recording_id}?include_file_url=false")
    assert response.status_code == 200
    assert "file_url" not in response.json() or response.json()["file_url"] is None

def test_recording_with_url_generation():
    # Test generating a fresh URL
    response = client.get(f"/api/v1/interviewer/interviews/{interview_key}/results/{session_id}/recordings/{recording_id}?generate_url=true&expires_in=1800")
    assert response.status_code == 200
    assert response.json()["file_url"] is not None
    # Verify URL expiration matches request
```

### 2. Batch Endpoint Tests

```python
def test_batch_analyze_endpoint():
    # Test renamed batch endpoint with multiple files
    files = [
        ("files", ("recording1.mp3", open("test_files/recording1.mp3", "rb"), "audio/mpeg")),
        ("files", ("recording2.mp3", open("test_files/recording2.mp3", "rb"), "audio/mpeg"))
    ]
    response = client.post(
        "/api/v1/candidates/batch/analyze",
        files=files,
        data={"job_name": "Test Batch", "enable_stress_analysis": "true"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["total_files"] == 2
```

### 3. Integration Tests

These tests will verify that the frontend applications correctly interact with the consolidated API endpoints, including:

1. Recording uploads with token-based authentication
2. Recording retrieval with new query parameters
3. Batch processing with the renamed endpoint

**Implementation Timeline:**
- Unit tests: Q3 2023
- Integration tests: Q3-Q4 2023
- Performance tests: Q4 2023

## Breaking Changes

### For Frontend Applications:
1. Update recording upload calls to use token-based authentication
2. Update recording download URLs to use simplified format parameter
3. Replace legacy session creation calls

### Migration Timeline:
- **Week 1-2**: Implement new consolidated endpoints
- **Week 3-4**: Add deprecation warnings to old endpoints  
- **Week 5-6**: Update documentation and client applications
- **Week 7-8**: Remove deprecated endpoints

## Risk Mitigation

1. **Backward Compatibility**: Keep old endpoints with deprecation warnings initially
2. **Gradual Migration**: Phased approach allows for testing at each step
3. **Documentation**: Clear migration guide for API consumers
4. **Testing**: Comprehensive testing of new consolidated endpoints

## Success Metrics

- Reduction in duplicate endpoints: Target 40-50% fewer recording-related endpoints
- Improved Swagger UI clarity: Consolidated endpoint groups
- Reduced support tickets related to API confusion
- Faster development time for new features due to clearer structure
