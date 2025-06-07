# API Reference for Frontend Development

**Current State:** May 27, 2025  
**Backend Version:** Latest  
**Base URL:** `http://localhost:8001` (Development)

## Overview

This document provides the complete API structure for frontend integration. All endpoints require authentication unless otherwise specified.

## Authentication

### Base Path: `/auth`

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `POST` | `/auth/register` | Register new user | `UserCreate` | `UserResponse` |
| `POST` | `/auth/login` | User login | `UserLogin` | `Token` |
| `POST` | `/auth/refresh` | Refresh access token | `RefreshToken` | `Token` |
| `POST` | `/auth/logout` | User logout | - | `Message` |
| `GET` | `/auth/me` | Get current user | - | `UserResponse` |
| `PUT` | `/auth/me` | Update user profile | `UserUpdate` | `UserResponse` |
| `POST` | `/auth/forgot-password` | Request password reset | `PasswordResetRequest` | `Message` |
| `POST` | `/auth/reset-password` | Reset password | `PasswordReset` | `Message` |

**Authentication Header:** `Authorization: Bearer {access_token}`

---

## Candidate Portal

### Base Path: `/candidates`

#### Interview Sessions
| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `POST` | `/candidates/interviews/` | Create new interview session | `InterviewCreate` | `InterviewResponse` |
| `GET` | `/candidates/interviews/` | List user's interviews | Query params | `List[InterviewResponse]` |
| `GET` | `/candidates/interviews/{interview_id}` | Get interview details | - | `InterviewResponse` |
| `PUT` | `/candidates/interviews/{interview_id}` | Update interview | `InterviewUpdate` | `InterviewResponse` |
| `DELETE` | `/candidates/interviews/{interview_id}` | Delete interview | - | `Message` |
| `POST` | `/candidates/interviews/{interview_id}/start` | Start interview session | - | `SessionStartResponse` |
| `POST` | `/candidates/interviews/{interview_id}/end` | End interview session | - | `SessionEndResponse` |

#### Identity Verification
| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `POST` | `/candidates/verify/identity` | Verify identity with document | `Multipart Form` | `VerificationResponse` |
| `GET` | `/candidates/verify/status/{verification_id}` | Check verification status | - | `VerificationStatus` |
| `POST` | `/candidates/verify/face` | Face verification | `Face image file` | `FaceVerificationResponse` |

#### Recording Management
| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `POST` | `/candidates/recordings/{interview_id}/upload` | Upload interview recording | `Multipart Form` | `UploadResponse` |
| `GET` | `/candidates/recordings/{interview_id}/download` | Download recording | - | `File Stream` |
| `DELETE` | `/candidates/recordings/{interview_id}` | Delete recording | - | `Message` |
| `GET` | `/candidates/recordings/{interview_id}/analysis` | Get analysis results | - | `AnalysisResponse` |
| `POST` | `/candidates/recordings/{interview_id}/transcribe` | Request transcription | - | `TranscriptionResponse` |

---

## Interviewer Panel

### Base Path: `/interviewer`

#### Interview Management
| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `POST` | `/interviewer/interviews/` | Create interview template | `InterviewTemplateCreate` | `InterviewTemplateResponse` |
| `GET` | `/interviewer/interviews/` | List interview templates | Query params | `List[InterviewTemplateResponse]` |
| `GET` | `/interviewer/interviews/{template_id}` | Get template details | - | `InterviewTemplateResponse` |
| `PUT` | `/interviewer/interviews/{template_id}` | Update template | `InterviewTemplateUpdate` | `InterviewTemplateResponse` |
| `DELETE` | `/interviewer/interviews/{template_id}` | Delete template | - | `Message` |
| `POST` | `/interviewer/interviews/{template_id}/invite` | Send interview invitation | `InvitationCreate` | `InvitationResponse` |
| `GET` | `/interviewer/interviews/invitations` | List sent invitations | Query params | `List[InvitationResponse]` |

#### Analytics & Insights
| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `GET` | `/interviewer/analytics/dashboard` | Get dashboard data | Query params | `DashboardData` |
| `GET` | `/interviewer/analytics/reports/{interview_id}` | Get interview report | - | `InterviewReport` |
| `GET` | `/interviewer/analytics/candidates/{candidate_id}` | Get candidate analytics | - | `CandidateAnalytics` |
| `GET` | `/interviewer/analytics/trends` | Get hiring trends | Query params | `TrendsData` |
| `POST` | `/interviewer/analytics/export` | Export analytics data | `ExportRequest` | `File Stream` |

#### Profile Management
| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `GET` | `/interviewer/profile/` | Get interviewer profile | - | `InterviewerProfile` |
| `PUT` | `/interviewer/profile/` | Update profile | `InterviewerProfileUpdate` | `InterviewerProfile` |
| `POST` | `/interviewer/profile/avatar` | Upload avatar | `Image file` | `AvatarResponse` |
| `GET` | `/interviewer/profile/preferences` | Get preferences | - | `UserPreferences` |
| `PUT` | `/interviewer/profile/preferences` | Update preferences | `UserPreferencesUpdate` | `UserPreferences` |

#### Settings
| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `GET` | `/interviewer/settings/notifications` | Get notification settings | - | `NotificationSettings` |
| `PUT` | `/interviewer/settings/notifications` | Update notifications | `NotificationSettingsUpdate` | `NotificationSettings` |
| `GET` | `/interviewer/settings/security` | Get security settings | - | `SecuritySettings` |
| `PUT` | `/interviewer/settings/security` | Update security | `SecuritySettingsUpdate` | `SecuritySettings` |
| `POST` | `/interviewer/settings/api-keys` | Generate API key | `ApiKeyCreate` | `ApiKeyResponse` |
| `DELETE` | `/interviewer/settings/api-keys/{key_id}` | Revoke API key | - | `Message` |

---

## Admin Panel

### Base Path: `/admin`

#### User Management
| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `GET` | `/admin/users/` | List all users | Query params | `List[UserResponse]` |
| `GET` | `/admin/users/{user_id}` | Get user details | - | `UserResponse` |
| `PUT` | `/admin/users/{user_id}` | Update user | `AdminUserUpdate` | `UserResponse` |
| `DELETE` | `/admin/users/{user_id}` | Delete user | - | `Message` |
| `POST` | `/admin/users/{user_id}/suspend` | Suspend user | `SuspensionReason` | `Message` |
| `POST` | `/admin/users/{user_id}/activate` | Activate user | - | `Message` |

#### System Management
| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `GET` | `/admin/system/stats` | Get system statistics | - | `SystemStats` |
| `GET` | `/admin/system/health` | System health check | - | `HealthCheck` |
| `GET` | `/admin/system/logs` | Get system logs | Query params | `List[LogEntry]` |
| `POST` | `/admin/system/maintenance` | Toggle maintenance mode | `MaintenanceToggle` | `Message` |

---

## Billing & Subscriptions

### Base Path: `/billing`

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| `GET` | `/billing/plans` | Get available plans | - | `List[SubscriptionPlan]` |
| `GET` | `/billing/subscription` | Get current subscription | - | `SubscriptionResponse` |
| `POST` | `/billing/subscribe` | Subscribe to plan | `SubscriptionCreate` | `SubscriptionResponse` |
| `PUT` | `/billing/subscription` | Update subscription | `SubscriptionUpdate` | `SubscriptionResponse` |
| `DELETE` | `/billing/subscription` | Cancel subscription | - | `Message` |
| `GET` | `/billing/invoices` | Get billing history | Query params | `List[Invoice]` |
| `GET` | `/billing/usage` | Get usage statistics | Query params | `UsageStats` |

---

## Common Query Parameters

### Pagination
- `page`: Page number (default: 1)
- `size`: Items per page (default: 10, max: 100)

### Filtering
- `search`: Search term
- `status`: Filter by status
- `date_from`: Start date (ISO format)
- `date_to`: End date (ISO format)
- `sort_by`: Sort field
- `sort_order`: "asc" or "desc" (default: "desc")

### Example
```
GET /interviewer/interviews/?page=1&size=20&search=software&status=active&sort_by=created_at&sort_order=desc
```

---

## Response Schemas

### Standard Response Wrapper
```typescript
interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  errors?: string[];
  pagination?: PaginationMeta;
}

interface PaginationMeta {
  page: number;
  size: number;
  total: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}
```

### Error Response
```typescript
interface ErrorResponse {
  success: false;
  message: string;
  errors?: string[];
  error_code?: string;
  timestamp: string;
}
```

---

## File Upload Guidelines

### Supported Formats
**Audio:** `.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`  
**Video:** `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`

### File Size Limits
- **Single file:** Max 500MB
- **Batch upload:** Max 50 files per batch
- **Total batch size:** Max 5GB

### Upload Headers
```
Content-Type: multipart/form-data
Authorization: Bearer {access_token}
```

---

## WebSocket Endpoints

### Real-time Updates
- **Interview Status:** `/ws/interview/{interview_id}/status`
- **Batch Processing:** `/ws/batch/{job_id}/progress`
- **Notifications:** `/ws/user/{user_id}/notifications`

**Connection:** `ws://localhost:8001/ws/{endpoint}`  
**Authentication:** Send token in first message or query parameter

---

## Rate Limits

| Endpoint Category | Limit | Window |
|------------------|-------|--------|
| Authentication | 5 requests | 1 minute |
| File Upload | 10 requests | 5 minutes |
| General API | 100 requests | 1 minute |
| Batch Processing | 5 jobs | 1 hour |

---

## Environment-Specific URLs

### Development
- **API Base:** `http://localhost:8001`
- **WebSocket:** `ws://localhost:8001/ws`
- **Docs:** `http://localhost:8001/docs`

### Production
- **API Base:** `https://api.interviewplatform.com`
- **WebSocket:** `wss://api.interviewplatform.com/ws`
- **Docs:** `https://api.interviewplatform.com/docs`

---

## Frontend Integration Notes

### Authentication Flow
1. Login to get access token
2. Store token in secure storage
3. Include token in all API requests
4. Handle token refresh automatically
5. Redirect to login on 401 errors

### File Upload Progress
```typescript
// Example for tracking upload progress
const uploadFile = async (file: File, onProgress: (progress: number) => void) => {
  const formData = new FormData();
  formData.append('file', file);
  
  return axios.post('/candidates/recordings/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      const progress = (progressEvent.loaded / progressEvent.total) * 100;
      onProgress(progress);
    }
  });
};
```

### Error Handling
```typescript
// Standard error handling
try {
  const response = await api.get('/endpoint');
  return response.data;
} catch (error) {
  if (error.response?.status === 401) {
    // Handle authentication error
    redirectToLogin();
  } else if (error.response?.status === 429) {
    // Handle rate limit
    showRateLimitMessage();
  } else {
    // Handle other errors
    showErrorMessage(error.response?.data?.message || 'An error occurred');
  }
}
```

### Real-time Updates
```typescript
// WebSocket connection example
const connectWebSocket = (endpoint: string, token: string) => {
  const ws = new WebSocket(`ws://localhost:8001/ws/${endpoint}?token=${token}`);
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleRealtimeUpdate(data);
  };
  
  return ws;
};
```

---

**Document Status:** ✅ Complete and Current  
**Last Updated:** May 27, 2025  
**Next Review:** When API changes are made