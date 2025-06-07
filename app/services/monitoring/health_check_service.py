"""
Health check service for monitoring system status.
Optimized for Heroku deployment.
"""
import os
import time
import platform
import psutil
import datetime
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.core.database.models import User

# Start time of the application
APP_START_TIME = time.time()
logger = logging.getLogger(__name__)

class HealthCheckService:
    """Service for checking the health of various system components."""
    
    @staticmethod
    def check_database(db: Session) -> Dict[str, Any]:
        """
        Check the database connection is working.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with database status information
        """
        try:
            # Simple query to test db connection
            result = db.execute(text("SELECT 1")).first()
            if result and result[0] == 1:
                return {
                    "status": "connected",
                    "message": "Database connection is healthy"
                }
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Database connection issue: {str(e)}"
            }
        
        return {
            "status": "unknown",
            "message": "Database check returned unexpected result"
        }
    
    @staticmethod
    def check_storage() -> Dict[str, Any]:
        """
        Check if the upload storage paths exist and are writable.
        
        Returns:
            Dictionary with storage status information
        """
        upload_dir = os.path.join(os.getcwd(), "uploads", "recordings")
        
        try:
            # Check if directory exists
            if not os.path.exists(upload_dir):
                # Try to create it
                try:
                    os.makedirs(upload_dir, exist_ok=True)
                except Exception as e:
                    logger.error(f"Cannot create upload directory: {str(e)}")
                    return {
                        "status": "error", 
                        "message": f"Upload directory doesn't exist and couldn't be created: {str(e)}"
                    }
            
            # Check if we can write to it
            test_file_path = os.path.join(upload_dir, ".health_check_test")
            with open(test_file_path, "w") as f:
                f.write("test")
            os.remove(test_file_path)
            
            return {
                "status": "available",
                "message": "Storage system is working correctly"
            }
        except Exception as e:
            logger.error(f"Storage health check failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Storage system issue: {str(e)}"
            }
    
    @staticmethod
    def check_uptime() -> str:
        """
        Calculate application uptime.
        
        Returns:
            String representing uptime in a human-readable format
        """
        uptime_seconds = int(time.time() - APP_START_TIME)
        
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days} days {hours} hours {minutes} minutes"
        elif hours > 0:
            return f"{hours} hours {minutes} minutes"
        elif minutes > 0:
            return f"{minutes} minutes {seconds} seconds"
        else:
            return f"{seconds} seconds"
    
    @staticmethod
    def check_processors() -> Dict[str, str]:
        """
        Check status of processing services.
        
        Returns:
            Dictionary with processor statuses
        """
        processors = {}
        
        # Check transcription service by checking OpenAI API key
        if settings.OPENAI_API_KEY:
            processors["transcription"] = "operational"
        else:
            processors["transcription"] = "unavailable"
        
        # Add any other processor checks here
        processors["analysis"] = "operational"
        
        return processors
    
    @staticmethod
    def get_full_status(db: Session) -> Dict[str, Any]:
        """
        Get complete system status information.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with complete system status
        """
        db_status = HealthCheckService.check_database(db)
        storage_status = HealthCheckService.check_storage()
        processors = HealthCheckService.check_processors()
        
        # Determine overall status
        overall_status = "operational"
        if db_status["status"] != "connected" or storage_status["status"] != "available":
            overall_status = "degraded"
        if db_status["status"] == "error" and storage_status["status"] == "error":
            overall_status = "critical"
        
        return {
            "status": overall_status,
            "database": db_status["status"],
            "storage": storage_status["status"],
            "processors": processors,
            "uptime": HealthCheckService.check_uptime(),
            "version": settings.VERSION,
            "environment": "production" if not settings.DEV_MODE else "development",
            "timestamp": datetime.datetime.now().isoformat()
        }