"""
Consolidated authentication and authorization module.
Provides security features for both user and admin authentication.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import logging

from app.core.config import settings
from app.core.database.db import get_db
from app.core.database.models import User, Admin
from app.schemas.auth_schemas import TokenData
from app.utils.datetime_utils import get_utc_now, safe_compare_dates
from app.utils.subscription_utils import update_subscription_status

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define OAuth2 schemes for different authentication paths
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="UserAuth"
)

admin_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/admin/auth/login",
    scheme_name="AdminAuth"
)

# Configure password hashing with bcrypt with better error handling
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

# ======================================================================
# SECTION: Password Management
# ======================================================================

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

def authenticate_admin(db: Session, username: str, password: str):
    """Authenticate an admin by username and password"""
    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin or not verify_password(password, admin.hashed_password):
        return False
    return admin

# ======================================================================
# SECTION: Token Management
# ======================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token with expiration.
    
    Works for both admin and regular user authentication by accepting
    different claim data.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# ======================================================================
# SECTION: User Authentication
# ======================================================================

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
    """
    Get the current authenticated user from JWT token.
    
    This function:
    1. Validates the JWT token
    2. Extracts the username claim
    3. Verifies the user exists in the database
    4. Checks subscription status
    5. Returns the user instance if all checks pass
    
    Parameters:
    - db: Database session
    - token: JWT token from request
    
    Returns:
    - User instance for the authenticated user
    
    Raises:
    - HTTP 401: If token is invalid
    - HTTP 403: If subscription is inactive
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the JWT token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        # Check if this is an admin token (should not be used for user routes)
        is_admin: bool = payload.get("is_admin", False)
        
        if username is None:
            raise credentials_exception
            
        # Prevent admin tokens from being used for user routes
        if is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin authentication used for user endpoint"
            )
            
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

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user with active subscription check.
    
    An additional layer of protection to ensure the user has an active subscription.
    """
    # Double-check the subscription status
    if not check_subscription_status(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your subscription is not active. Please renew your subscription."
        )
    return current_user

# ======================================================================
# SECTION: Admin Authentication
# ======================================================================

async def get_current_admin(
    db: Session = Depends(get_db), 
    token: str = Depends(admin_oauth2_scheme)
):
    """
    Get the current authenticated admin from JWT token.
    
    This function:
    1. Validates the JWT token
    2. Extracts the admin username and verifies the is_admin claim
    3. Verifies the admin exists in the database
    4. Checks that the admin account is active
    5. Returns the admin instance if all checks pass
    
    Parameters:
    - db: Database session
    - token: JWT token from request
    
    Returns:
    - Admin instance for the authenticated admin
    
    Raises:
    - HTTP 401: If token is invalid
    - HTTP 403: If admin account is inactive
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid admin authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the JWT token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        is_admin: bool = payload.get("is_admin", False)
        
        # Validate token claims
        if username is None:
            logger.warning("Admin token missing 'sub' claim")
            raise credentials_exception
            
        if not is_admin:
            logger.warning("Non-admin token used for admin authentication")
            raise credentials_exception
            
        token_data = TokenData(username=username)
    except JWTError as e:
        logger.warning(f"JWT error in admin authentication: {str(e)}")
        raise credentials_exception
    
    # Ensure we have fresh data
    db.expire_all()
    
    # Get admin from database
    admin = db.query(Admin).filter(Admin.username == token_data.username).first()
    
    if admin is None:
        logger.warning(f"Admin not found in database: {token_data.username}")
        raise credentials_exception
    
    # Check if admin account is active
    if not admin.is_active:
        logger.warning(f"Inactive admin account: {admin.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive"
        )
    
    return admin

# Function to seed the first admin account from environment variables
# This is used during system startup to ensure there's at least one admin account
def seed_admin_account(db: Session) -> Optional[Admin]:
    """
    Create an initial admin account from environment variables if no admins exist.
    
    This function is called during system startup to ensure there's at least one
    admin account in the system. It only creates an account if no admins exist.
    
    Parameters:
    - db: Database session
    
    Returns:
    - Created admin instance or None if no account was created
    """
    # Check if any admin accounts exist
    admin_count = db.query(Admin).count()
    
    if admin_count == 0 and settings.ADMIN_USERNAME and settings.ADMIN_PASSWORD:
        logger.info("No admin accounts found. Creating initial admin account.")
        
        # Create admin account from environment variables
        admin = Admin(
            username=settings.ADMIN_USERNAME,
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            email=f"{settings.ADMIN_USERNAME}@example.com",  # Default email
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        
        try:
            db.add(admin)
            db.commit()
            db.refresh(admin)
            logger.info(f"Initial admin account created: {admin.username}")
            return admin
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create initial admin account: {str(e)}")
            return None
    
    return None