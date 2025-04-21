"""
Endpoints for system administration and monitoring.
These endpoints provide administrative functionality for managing system-level operations
such as database maintenance, subscription synchronization, and other administrative tasks.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
import secrets
import logging
from typing import Dict, Any

from app.api.deps import db_dependency
from app.core.config import settings
from app.utils.subscription_utils import sync_all_subscription_statuses

# Basic authentication for admin endpoints
security = HTTPBasic()
logger = logging.getLogger(__name__)

# Create router
admin_router = APIRouter()

def get_admin_auth(credentials: HTTPBasicCredentials = Security(security)):
    """
    Verify admin credentials using HTTP Basic Auth.
    
    This function performs credential verification for administrative endpoints.
    It uses constant-time comparison to prevent timing attacks.
    
    Parameters:
    - **credentials**: Username and password from HTTP Basic Auth
    
    Returns:
    - True if credentials are valid
    
    Raises:
    - HTTP 401: If credentials are invalid
    """
    correct_username = secrets.compare_digest(credentials.username, settings.ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, settings.ADMIN_PASSWORD)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

@admin_router.post("/refresh-db", 
                 status_code=status.HTTP_200_OK,
                 summary="Refresh Database Connection",
                 description="Force refresh of database connection and cache",
                 response_model=Dict[str, str])
def refresh_database(
    db: Session = db_dependency,
    _: bool = Depends(get_admin_auth)
):
    """
    Force refresh of database connection and cache.
    
    This endpoint is used for troubleshooting database connection issues
    by clearing cached data and testing the connection directly.
    
    It's particularly useful when:
    - Database connections appear to be stale
    - Data inconsistencies are observed
    - After server maintenance activities
    
    Returns:
    - Success message
    
    Raises:
    - HTTP 500: If database refresh fails
    """
    try:
        # Clear any cached data
        db.expire_all()
        # Execute a simple query to test connection
        db.execute(text("SELECT 1"))
        db.commit()
        return {"message": "Database connection refreshed successfully"}
    except Exception as e:
        logger.error(f"Error refreshing database: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh database: {str(e)}"
        )

@admin_router.post("/sync-subscriptions", 
                 status_code=status.HTTP_200_OK,
                 summary="Synchronize Subscriptions",
                 description="Manually trigger synchronization of all user subscription statuses",
                 response_model=Dict[str, str])
def sync_subscriptions(
    db: Session = db_dependency,
    _: bool = Depends(get_admin_auth)
):
    """
    Manually trigger synchronization of subscription statuses.
    
    This endpoint ensures the system's subscription status data is up-to-date by:
    1. Checking all users with subscription_end_date values
    2. Comparing against current date
    3. Updating the is_active and subscription_status fields
    
    This is useful when:
    - Users report subscription status issues
    - After system maintenance
    - To ensure data consistency
    
    Returns:
    - Success message with count of synchronized records
    
    Raises:
    - HTTP 500: If synchronization process fails
    """
    try:
        count = sync_all_subscription_statuses(db)
        return {"message": f"Synchronized {count} subscription records"}
    except Exception as e:
        logger.error(f"Error syncing subscriptions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync subscriptions: {str(e)}"
        )