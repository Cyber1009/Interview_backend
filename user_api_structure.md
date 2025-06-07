# Current API Endpoint Structure Documentation

## Overview
This document provides a comprehensive overview of the current API endpoint structure for the Interview Management Platform. This documentation is intended for frontend development teams to understand available endpoints, their purposes, and expected request/response formats.

## Base URL Structure
- **Development**: `http://localhost:8000/api/v1`
- **Production**: `https://your-domain.com/api/v1`

## Authentication
- **User Endpoints**: Bearer JWT token in Authorization header
- **Admin Endpoints**: Admin JWT token in Authorization header  
- **Candidate Endpoints**: Token-based authentication using interview tokens
- **Public Endpoints**: No authentication required

## API Endpoint Organization

### 1. Authentication & User Management (`/auth`)

#### User Authentication
```
POST   /auth/login                    # User login
POST   /auth/logout                   # User logout  
POST   /auth/refresh                  # Refresh JWT token
POST   /auth/change-password          # Change user password
```

#### Account Registration
```
POST   /auth/registration/            # Register new account (pending activation)
```

**Example Registration Request:**
```json
{
  "username": "interviewer1",
  "password": "securePassword123",
  "email": "interviewer@example.com",
  "company": "Example Corp"
}
```

**Example Login Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJI...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "interviewer1",
    "email": "interviewer@example.com",
    "company": "Example Corp",
    "subscription_status": "active",
    "subscription_plan": "professional"
  }
}
```

### 2. Interviewer Panel (`/interviewer`)

#### Interview Management
```
GET    /interviewer/interviews                           # List all interviews
POST   /interviewer/interviews                           # Create new interview
GET    /interviewer/interviews/{interview_key}           # Get interview details
PUT    /interviewer/interviews/{interview_key}           # Update interview
DELETE /interviewer/interviews/{interview_key}           # Delete interview
PUT    /interviewer/interviews/{interview_key}/update-with-questions  # Bulk update
```

**Example Interview Creation:**
```json
{
  "title": "Software Developer Interview",
  "questions": [
    {
      "text": "Tell me about your experience with Python",
      "preparation_time": 30.0,
      "responding_time": 90.0,
      "order": 1
    },
    {
      "text": "Describe a challenging project you worked on",
      "preparation_time": 45.0,
      "responding_time": 120.0,
      "order": 2
    }
  ]
}
```

#### Question Management
```
GET    /interviewer/interviews/{interview_key}/questions              # List questions
POST   /interviewer/interviews/{interview_key}/questions              # Add question
PUT    /interviewer/interviews/{interview_key}/questions/{question_id} # Update question
DELETE /interviewer/interviews/{interview_key}/questions/{question_id} # Delete question
PUT    /interviewer/interviews/{interview_key}/questions/reorder      # Reorder questions
```

**Example Question:**
```json
{
  "text": "What is your experience with React?",
  "preparation_time": 30.0,
  "responding_time": 60.0
}
```

#### Token Management
```
GET    /interviewer/interviews/{interview_key}/tokens     # List interview tokens
POST   /interviewer/interviews/{interview_key}/tokens     # Create candidate token
DELETE /interviewer/interviews/{interview_key}/tokens/{token_id} # Delete token
```

**Example Token Creation (Enhanced):**
```json
{
  "interview_id": 123,
  "candidate_name": "John Doe",
  "expires_in_hours": 72,
  "max_attempts": 1
}
```

**Example Token Response:**
```json
{
  "token_value": "abc123def456ghi789",
  "candidate_name": "John Doe",
  "is_used": false,
  "expires_at": "2024-01-15T10:30:00Z",
  "max_attempts": 1,
  "current_attempts": 0,
  "created_at": "2024-01-12T10:30:00Z"
}
```

#### Results and Analytics
```
GET    /interviewer/interviews/{interview_key}/results                    # List all session results
GET    /interviewer/interviews/{interview_key}/results/{session_id}       # Get specific session
GET    /interviewer/interviews/{interview_key}/results/{session_id}/recordings/{recording_id} # Recording details
DELETE /interviewer/interviews/{interview_key}/results/{session_id}       # Delete session
```

#### Manual Batch Processing (For Failed Sessions)
```
POST   /interviewer/interviews/{interview_key}/results/{session_id}/batch-process  # Manual batch processing
GET    /interviewer/interviews/{interview_key}/results/{session_id}/batch-status   # Check processing status
```

**Example Batch Process Request:**
```json
{
  "transcribe": true,
  "analyze": true,
  "force_retranscribe": false,
  "force_reanalyze": false
}
```

#### Profile and Settings
```
GET    /interviewer/profile                # Get user profile
PUT    /interviewer/profile                # Update profile
GET    /interviewer/settings               # Get user settings
PUT    /interviewer/settings               # Update settings
GET    /interviewer/settings/theme         # Get theme customization
PUT    /interviewer/settings/theme         # Update theme
DELETE /interviewer/settings/theme/logo    # Delete company logo
```

**Example Theme Update:**
```json
{
  "primary_color": "#091326",
  "accent_color": "#52606d", 
  "background_color": "#f5f7fa",
  "text_color": "#222222",
  "company_logo": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
}
```

#### Analytics Dashboard
```
GET    /interviewer/analytics/overview     # Dashboard overview data
GET    /interviewer/analytics/interviews   # Interview-specific analytics
GET    /interviewer/analytics/candidates   # Candidate performance analytics
```

### 3. Candidate Portal (`/candidates`)

#### Interview Access and Session Management
```
POST   /candidates/interviews/access           # Access interview details (no session creation)
POST   /candidates/interviews/start-session    # Start new interview session
PATCH  /candidates/interviews/complete-session # Complete interview session (triggers auto-processing)
```

**Example Interview Access:**
```json
{
  "token": "abc123def456ghi789"
}
```

**Example Access Response:**
```json
{
  "interview": {
    "id": 123,
    "title": "Software Developer Interview", 
    "questions": [
      {
        "id": 1,
        "text": "Tell me about yourself",
        "preparation_time": 30.0,
        "responding_time": 90.0,
        "order": 1
      }
    ]
  },
  "theme": {
    "primary_color": "#091326",
    "accent_color": "#52606d",
    "background_color": "#f5f7fa", 
    "text_color": "#222222",
    "company_logo": "https://example.com/logo.png"
  },
  "token_info": {
    "expires_at": "2024-01-15T10:30:00Z",
    "attempts_remaining": 1
  }
}
```

#### Recording Management
```
POST   /candidates/interviews/recordings    # Upload recording for question
```

**Example Recording Upload:**
```javascript
// Form data upload
const formData = new FormData();
formData.append('session_id', '456');
formData.append('question_id', '1');
formData.append('audio_file', audioBlob, 'recording.webm');

fetch('/api/v1/candidates/interviews/recordings', {
  method: 'POST',
  body: formData
});
```

**Example Recording Response:**
```json
{
  "id": 789,
  "session_id": 456,
  "question_id": 1,
  "file_path": "/uploads/recordings/session_456_question_1.webm",
  "transcript": null,
  "analysis": null,
  "created_at": "2024-01-12T11:00:00Z"
}
```

### 4. Admin Panel (`/admin`)

#### Admin Authentication
```
POST   /admin/auth/login                # Admin login
POST   /admin/auth/change-password      # Change admin password
```

#### User Account Management
```
GET    /admin/users                     # List all users (with filters)
GET    /admin/users/pending             # List pending accounts
GET    /admin/users/{user_id}           # Get user details
POST   /admin/users                     # Create user account
PUT    /admin/users/{user_id}           # Update user account
DELETE /admin/users/{user_id}           # Delete user account
```

**Example User Filters:**
```
GET /admin/users?subscription_status=active&sort=created_at&order=desc&limit=50&offset=0
```

**Example User Update:**
```json
{
  "email": "updated@example.com",
  "company": "New Company Name",
  "is_active": true,
  "subscription_status": "active",
  "subscription_plan": "professional",
  "subscription_end_date": "2025-12-31T23:59:59Z"
}
```

#### System Management
```
GET    /admin/system/status             # System health status
GET    /admin/system/metrics            # System performance metrics
POST   /admin/system/fix-invalid-questions  # Fix data issues
```

**Example System Status Response:**
```json
{
  "status": "operational",
  "database": "connected",
  "storage": "available", 
  "processors": {
    "transcription": "operational",
    "analysis": "operational"
  },
  "uptime": "7 days 5 hours",
  "version": "1.0.0"
}
```

### 5. Billing and Subscriptions (`/billing`)

#### Subscription Management
```
GET    /billing/subscription/info       # Current subscription details
GET    /billing/subscription/plans      # Available subscription plans
POST   /billing/subscription/cancel     # Cancel subscription
```

**Example Subscription Info:**
```json
{
  "plan": "professional",
  "status": "active",
  "current_period_end": "2024-02-12T10:30:00Z",
  "cancel_at_period_end": false,
  "next_invoice": "2024-02-12T10:30:00Z"
}
```

#### Checkout and Payment
```
POST   /billing/checkout/subscription/{plan_id}           # Create subscription checkout
POST   /billing/checkout/reactivate-subscription/{plan_id} # Reactivate subscription
POST   /billing/checkout/registration/{plan_id}           # Registration with subscription
POST   /billing/checkout/registration/complete            # Complete registration
GET    /billing/checkout/customer-portal                  # Access Stripe customer portal
```

**Example Checkout Response:**
```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_test_...",
  "session_id": "cs_test_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
}
```

#### Webhook Handling
```
POST   /billing/webhook                 # Stripe webhook endpoint (internal)
```

## Response Format Standards

### Success Responses
All successful responses follow consistent patterns:

```json
{
  "id": 123,
  "field1": "value1",
  "field2": "value2",
  "created_at": "2024-01-12T10:30:00Z",
  "updated_at": "2024-01-12T11:30:00Z"
}
```

### Error Responses
All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `204` - No Content (for deletions)
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (authentication required)
- `402` - Payment Required (insufficient credits)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `422` - Unprocessable Entity (validation errors)
- `500` - Internal Server Error

### Pagination
List endpoints support pagination:

```
GET /admin/users?limit=50&offset=0&sort=created_at&order=desc
```

**Pagination Response Format:**
```json
{
  "items": [...],
  "total": 150,
  "limit": 50,
  "offset": 0,
  "has_next": true,
  "has_prev": false
}
```

## Authentication Headers

### User Endpoints
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJI...
Content-Type: application/json
```

### Admin Endpoints  
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJI...
Content-Type: application/json
```

### File Uploads
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJI...
Content-Type: multipart/form-data
```

## Rate Limiting
- **Authentication endpoints**: 10 requests per minute
- **General API endpoints**: 100 requests per minute
- **File upload endpoints**: 20 requests per minute

## Frontend Integration Notes

### 1. Token Management for Candidates
- Tokens are single-use and expire after a set time (default 72 hours)
- Always check token validity before starting sessions
- Handle token expiration gracefully with clear error messages

### 2. File Upload Handling
- Use `FormData` for audio file uploads
- Support progress tracking for large files
- Implement retry logic for failed uploads

### 3. Real-time Updates
- Session completion triggers background processing
- Use polling or webhooks to check processing status
- Provide progress indicators for long-running operations

### 4. Error Handling
- Implement consistent error handling across all endpoints
- Show user-friendly messages for common errors
- Log technical errors for debugging

### 5. Credit System (Future Enhancement)
- Monitor credit balance before allowing session completion
- Display clear credit consumption information
- Provide upgrade prompts when credits are low

This API structure provides a comprehensive foundation for building a modern interview management platform with clear separation of concerns and consistent patterns across all user types.