"""
Authentication and authorization module providing security features.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import logging

from app.core.config import settings
from app.core.database.db import get_db
from app.core.database.models import User
from app.schemas.auth_schemas import TokenData
from app.utils.datetime_utils import get_utc_now, safe_compare_dates
from app.utils.subscription_utils import update_subscription_status

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define OAuth2 scheme here as the single source of truth for token URL
# This is used across the application for authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Configure password hashing with bcrypt with better error handling
# This implementation includes fallback options to handle different bcrypt versions
# across deployment environments
try:
    # First attempt with default settings
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    # Verify the context is working by hashing a test string
    test_hash = pwd_context.hash("test_password")
    logger.info("BCrypt initialized with default settings")
except Exception as e:
    logger.warning(f"Error initializing bcrypt with default settings: {e}")
    try:
        # Second attempt with explicit rounds configuration
        pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12  # Explicitly set rounds
        )
        # Verify the context is working
        test_hash = pwd_context.hash("test_password")
        logger.info("BCrypt initialized with explicit rounds setting")
    except Exception as e2:
        logger.error(f"Failed to initialize bcrypt with modified settings: {e2}")
        # Last resort - try with reduced complexity if on limited environments
        try:
            pwd_context = CryptContext(
                schemes=["bcrypt"],
                deprecated="auto",
                bcrypt__rounds=8  # Lower rounds for compatibility
            )
            logger.warning("BCrypt initialized with reduced security settings - update your environment")
        except Exception as e3:
            logger.critical(f"Cannot initialize password hashing: {e3}")
            raise RuntimeError("Failed to initialize password hashing mechanism")

def verify_password(plain_password, hashed_password):
    """Verify a password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hash a password for storage"""
    return pwd_context.hash(password)

def authenticate_user(db: Session, username: str, password: str):
    """Authenticate a user by username and password"""
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token with expiration"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def check_subscription_status(user: User, db: Session) -> bool:
    """
    Check if a user's subscription is active.
    
    This is used for redirecting expired users to subscription renewal.
    Returns True if subscription is active, False otherwise.
    """
    # Make sure we have fresh data
    db.refresh(user)
    
    # Update subscription status based on current date
    update_subscription_status(user, db)
    
    # Check if subscription is active
    if not user.is_active or user.subscription_status != "active":
        return False
    
    # Check if subscription end date is in the past
    now = get_utc_now()
    if user.subscription_end_date and user.subscription_end_date < now:
        user.subscription_status = "expired"
        user.is_active = False
        db.commit()
        return False
    
    return True

async def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    """Get the current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    # Explicitly refresh the session to ensure no stale data
    db.expire_all()
    
    # Get fresh user data
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    
    # Update the user's subscription status based on the subscription end date
    update_subscription_status(user, db)
    
    # Now check if they're active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your subscription has {user.subscription_status}. Please contact support to reactivate your account."
        )
        
    return user