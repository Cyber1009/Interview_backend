"""
Application configuration settings.
"""
import os
import sys

# Try to import from pydantic_settings first (newer versions)
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fall back to pydantic for older versions
    from pydantic import BaseSettings

class Settings(BaseSettings):
    # Determine if we're in development mode
    DEV_MODE: bool = os.getenv("DEV_MODE", "True").lower() in ("true", "1", "t")
    
    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:postgres@localhost/interview_db"
    )
    
    # Use SQLite as fallback in development mode if PostgreSQL connection fails
    SQLITE_URL: str = "sqlite:///./interview.db"
    
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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # OpenAI API key for Whisper
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
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

    class Config:
        env_file = ".env"

settings = Settings()