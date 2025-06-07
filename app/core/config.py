# Full updated config.py for reference
"""
Application configuration settings.
"""
import os
import sys
from typing import Dict, Any, List

# Try to import from pydantic_settings first (newer versions)
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fall back to pydantic for older versions
    from pydantic import BaseSettings

# Subscription plans configuration
SUBSCRIPTION_PLANS = {
    "basic": {
        "name": "Basic",
        "price_id": os.getenv("STRIPE_BASIC_PRICE_ID", ""),
        "price": 49,
        "duration_days": 30,
        "features": [
            "Up to 10 candidates per month",
            "Basic analytics",
            "Email support"
        ]
    },
    "premium": {
        "name": "Premium",
        "price_id": os.getenv("STRIPE_PREMIUM_PRICE_ID", ""),
        "price": 99,
        "duration_days": 30,
        "features": [
            "Up to 50 candidates per month",
            "Advanced analytics",
            "Priority email support",
            "Custom branding"
        ]
    },
    "enterprise": {
        "name": "Enterprise",
        "price_id": os.getenv("STRIPE_ENTERPRISE_PRICE_ID", ""),
        "price": 299,
        "duration_days": 30,
        "features": [
            "Unlimited candidates",
            "Custom question sets",
            "Dedicated account manager",
            "API access",
            "Advanced integrations"
        ]
    }
}

class SubscriptionPlansConfig:
    @staticmethod
    def get_plans() -> Dict:
        """Return all subscription plans."""
        return SUBSCRIPTION_PLANS
    
    @staticmethod
    def get_price_id(plan_id: str) -> str:
        """Return the price ID for a specific plan."""
        if plan_id not in SUBSCRIPTION_PLANS:
            return ""
        return SUBSCRIPTION_PLANS[plan_id].get("price_id", "")
    
    @staticmethod
    def get_duration_days(plan_id: str) -> int:
        """Return the duration in days for a specific plan."""
        if plan_id not in SUBSCRIPTION_PLANS:
            return 30  # Default to 30 days
        return SUBSCRIPTION_PLANS[plan_id].get("duration_days", 30)

class Settings(BaseSettings):
    # Application version
    VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    
    # Determine if we're in development mode
    DEV_MODE: bool = os.getenv("DEV_MODE", "True").lower() in ("true", "1", "t")
      # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:postgres@localhost/interview_db"
    )
    
    # SQLite configuration - commented out since not needed for deployment
    # SQLITE_URL: str = "sqlite:///./interview.db"
    
    # If using Heroku, adjust the DATABASE_URL to be compatible with SQLAlchemy
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # Subscription settings
    SUBSCRIPTION_CHECK_ENABLED: bool = os.getenv("SUBSCRIPTION_CHECK_ENABLED", "False").lower() in ("true", "1", "t")
    SUBSCRIPTION_API_KEY: str = os.getenv("SUBSCRIPTION_API_KEY", "")
    SUBSCRIPTION_API_URL: str = os.getenv("SUBSCRIPTION_API_URL", "")
    
    # Admin credentials for managing users
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin")  # Change in production!
    
    # JWT settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours    # OpenAI API key for Whisper
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Transcription settings
    USE_OPENAI_WHISPER: bool = os.getenv("USE_OPENAI_WHISPER", "false").lower() in ("true", "1", "t")
    TRANSCRIPTION_BACKEND: str = os.getenv("TRANSCRIPTION_BACKEND", "openai_api")  # "openai_api" or "local_whisper"
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "base")  # tiny, base, small, medium, large
    USE_FALLBACK_TRANSCRIPTION: bool = os.getenv("USE_FALLBACK_TRANSCRIPTION", "true").lower() == "true"  # Enable fallback to local whisper
    
    # App settings
    PORT: int = int(os.getenv("PORT", 8000))
    
    # Frontend URL (for redirects)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Stripe API settings
    STRIPE_API_KEY: str = os.getenv("STRIPE_API_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_BASIC_PRICE_ID: str = os.getenv("STRIPE_BASIC_PRICE_ID", "")
    STRIPE_PREMIUM_PRICE_ID: str = os.getenv("STRIPE_PREMIUM_PRICE_ID", "")
    STRIPE_ENTERPRISE_PRICE_ID: str = os.getenv("STRIPE_ENTERPRISE_PRICE_ID", "")
    
    # AWS S3 settings for file storage (important for Heroku deployment)
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_STORAGE_BUCKET_NAME: str = os.getenv("AWS_STORAGE_BUCKET_NAME", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_S3_CUSTOM_DOMAIN: str = os.getenv("AWS_S3_CUSTOM_DOMAIN", "")  # Optional CloudFront domain
    
    # Storage configuration with explicit controls per content type
    USE_S3_FOR_VIDEO: bool = os.getenv("USE_S3_FOR_VIDEO", "false").lower() == "true"
    USE_S3_FOR_LOGOS: bool = os.getenv("USE_S3_FOR_LOGOS", "false").lower() == "true"
    
    @property
    def should_use_s3(self) -> bool:
        """
        Determine if S3 storage should be used for video/recording files.
        Returns True only if:
        1. USE_S3_FOR_VIDEO is explicitly set to true, AND
        2. AWS credentials are available
        
        If USE_S3_FOR_VIDEO is False, always returns False regardless of credentials.
        """
        # If USE_S3_FOR_VIDEO is False, don't use S3 even if credentials exist
        if not self.USE_S3_FOR_VIDEO:
            return False
            
        # Only if USE_S3_FOR_VIDEO is True, check if credentials are available
        return bool(
            self.AWS_ACCESS_KEY_ID and 
            self.AWS_SECRET_ACCESS_KEY and 
            self.AWS_STORAGE_BUCKET_NAME
        )
    @property
    def should_use_s3_for_logos(self) -> bool:
        """
        Determine if S3 storage should be used specifically for logos.
        This allows separate control for logo storage vs other files.
        Returns True only if:
        1. USE_S3_FOR_LOGOS is explicitly set to true, AND
        2. AWS credentials are available
        
        If USE_S3_FOR_LOGOS is False, always returns False regardless of credentials.
        """
        # If USE_S3_FOR_LOGO is False, don't use S3 even if credentials exist
        if not self.USE_S3_FOR_LOGOS:
            return False
            
        # Use S3 if credentials are available (regardless of DEV_MODE)
        return bool(
            self.AWS_ACCESS_KEY_ID and 
            self.AWS_SECRET_ACCESS_KEY and 
            self.AWS_STORAGE_BUCKET_NAME
        )

    class Config:
        env_file = ".env"

settings = Settings()
