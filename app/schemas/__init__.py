"""
Schema package for the Interview Management Platform.

This package contains all Pydantic models used for request validation,
response serialization, and data transfer between API layers.

The schemas are organized following a domain-driven design pattern:
- base_schemas: Core base schemas used across multiple domains
- common_schemas: Shared schemas to prevent circular imports
- auth_schemas: Authentication, user, and admin account schemas
- interview_schemas: Interview, questions, and tokens schemas
- recording_schemas: Recording and transcription schemas
- payment_schemas: Payment and subscription schemas
- theme_schemas: Theme and UI customization schemas
"""

# Base schemas for cross-domain use
from app.schemas.base_schemas import (
    # Core base schemas
    EntityBase,
    TimestampBase,
    
    # User-related base schemas
    UserBase,
    UserCredentialsBase,
    
    # Subscription-related base schemas
    SubscriptionBase,
    
    # Token-related base schemas
    VerificationBase,
    CandidateTokenBase
)

# Common schemas for resolving circular dependencies
from app.schemas.common_schemas import (
    RecordingResponseBase,
    AnalysisResultBase
)

# Authentication and Admin schemas
from app.schemas.auth_schemas import (
    # Registration schemas
    RegistrationCreate,
    RegistrationResponse,
    AccountActivation,
    
    # User management schemas
    UserCreate,
    UserUpdate,
    UserResponse,
    UserProfile,  # Main user profile schema
    
    # Authentication schemas
    AuthToken,
    TokenData,
    PasswordChange,
    
    # Admin schemas
    AdminUserCreate,
    AdminUserUpdate,
    AdminActivateAccount,
    AdminUserResponse,
    AdminLogin,
    AdminCreate,
    AdminResponse,
    AdminUpdate,
    AdminToken
)

# Admin system schemas
from app.schemas.admin_schemas import (
    SystemConfigUpdate,
    SystemStatusResponse,
    MonitoringMetricsResponse
)

# Payment and checkout schemas
from app.schemas.payment_schemas import (
    # Checkout schemas
    CheckoutSession,
    CustomerPortalSession,
    
    # Registration flow schemas
    RegistrationCheckout,
    RegistrationComplete,
    
    # Subscription schemas
    SubscriptionPlanFeatures,
    SubscriptionPlanList,
    SubscriptionInfo,
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    
    # Webhook schemas
    WebhookEvent
)

# Theme schemas
from app.schemas.theme_schemas import (
    UserTheme,
    DEFAULT_PRIMARY_COLOR,
    DEFAULT_ACCENT_COLOR,
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_TEXT_COLOR
)

# Interview and question schemas
from app.schemas.interview_schemas import (
    # Question schemas
    QuestionBase,
    QuestionResponse,
    QuestionOrderUpdate,
    QuestionUpdateOrCreate,
    QuestionListResponse,
      # Interview schemas
    InterviewBase,
    InterviewCreateWithQuestions,
    InterviewResponse,
    InterviewUpdateWithQuestions,
    InterviewListResponse,
    EnhancedInterviewResponse,
    
    # Token schemas
    CandidateTokenCreate,
    CandidateTokenResponse,
    TokenVerifyResponse,
    
    # Session schemas
    SessionResponse,
    InterviewResult
)

# Recording and analysis schemas
from app.schemas.recording_schemas import (
    # Recording schemas
    RecordingBase,
    RecordingCreate,
    RecordingResponse,
    RecordingWithTranscription,
    
    # Transcription schemas
    TranscriptionRequest,
    TranscriptionResponse,
    
    # Analysis schemas
    AnalysisBase,
    KeywordExtractionResponse,
    SentimentAnalysisResponse,
    InterviewAnalysisQuestionResponse,
    InterviewAnalysisResponse,
    AnalysisScores,
    EnhancedInterviewAnalysisResponse,
    RecordingDetails
)
