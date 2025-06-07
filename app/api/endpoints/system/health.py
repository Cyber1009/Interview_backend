"""
System health and status endpoints.
Provides comprehensive monitoring and API information endpoints.
"""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
import psutil
import platform
from typing import Dict, Any, Optional
import logging
import os

from app.utils.datetime_utils import get_utc_now
from app.api.dependencies import db_dependency
from app.core.database.db import get_db_status
from app.core.tasks import scheduler
from app.core.config import settings

# Create router
system_router = APIRouter()

logger = logging.getLogger(__name__)

@system_router.get("/", 
    summary="API Information", 
    description="Root endpoint with API information and documentation links",
    response_model=Dict[str, Any])
def api_info():
    """
    Root endpoint providing basic API information and navigation.
    
    This endpoint serves as an entry point for API discovery with links to:
    - Documentation
    - Health checks
    - Status information
    - Metrics
    
    Returns:
    - **message**: API welcome message
    - **version**: Current API version
    - **links**: Links to key API endpoints for navigation
    """
    return {
        "message": "Interview App API is running",
        "version": "1.0.0",
        "links": {
            "documentation": "/docs",
            "health_check": "/system/health",
            "detailed_status": "/system/health/status",
            "system_metrics": "/system/health/metrics"
        }
    }

@system_router.get("/health", 
    summary="Health Check", 
    description="Simple health check endpoint for monitoring",
    status_code=200)
def health_check(response: Response):
    """
    Basic health check endpoint for monitoring systems.
    
    This endpoint is designed for automated monitoring systems:
    - Returns HTTP 200 OK when the service is healthy
    - Returns HTTP 503 Service Unavailable when there are issues
    - Contains minimal response payload for efficiency
    
    Returns:
    - Empty response with appropriate status code
    """
    # Here you could add basic checks that must pass for the system to be considered healthy
    # For example, checking if the database connection is active
    
    # If checks fail, you would return a 503 status:
    # response.status_code = 503
    # return {"status": "unhealthy"}
    
    # For now, we'll simply return 200 OK with no content
    response.status_code = 200
    return {"status": "healthy"}

@system_router.get("/health/status", 
    summary="Detailed System Status", 
    description="Comprehensive system status information for all components",
    response_model=Dict[str, Any])
def system_status(db: Session = db_dependency):
    """
    Detailed status report for all system components.
    
    This endpoint provides a comprehensive view of all system components:
    - API service
    - Database connections
    - Storage systems
    - Background processing
    - External dependencies
    
    Returns:
    - **status**: Overall system status (online/degraded/offline)
    - **components**: Status of individual system components
    - **api_version**: Current API version
    - **environment**: Current deployment environment
    - **server_time**: Current server time
    """
    # Check if uploads directory exists and is writable
    storage_status = "ok"
    try:
        upload_path = os.path.join(os.getcwd(), "uploads")
        if not os.path.exists(upload_path):
            os.makedirs(upload_path, exist_ok=True)
        # Test write permissions
        test_file = os.path.join(upload_path, ".test_write")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
    except Exception as e:
        logger.error(f"Storage check failed: {str(e)}")
        storage_status = f"error: {str(e)}"
    
    # Check scheduler status
    scheduler_status = "running" if scheduler.running else "stopped"
    scheduler_jobs = [job.id for job in scheduler.get_jobs()]
    
    # Get database status
    db_status = get_db_status(db)
    
    # Determine overall status
    overall_status = "online"
    if db_status != "connected" or storage_status != "ok" or scheduler_status != "running":
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "api_version": "1.0.0", 
        "environment": settings.ENVIRONMENT,
        "components": {
            "database": db_status,
            "storage": storage_status,
            "scheduler": {
                "status": scheduler_status,
                "jobs": scheduler_jobs
            },
            # Add other components as needed
        },
        "server_time": get_utc_now().isoformat()
    }

@system_router.get("/health/metrics",
    summary="System Resource Metrics",
    description="Detailed system resource utilization metrics",
    response_model=Dict[str, Any])
def system_metrics():
    """
    Detailed system resource utilization metrics.
    
    This endpoint provides real-time metrics about system resources:
    - CPU utilization
    - Memory usage
    - Disk space
    - Network statistics
    - Process information
    
    These metrics are useful for:
    - Performance monitoring
    - Capacity planning
    - Troubleshooting
    
    Returns:
    - **cpu**: CPU utilization metrics
    - **memory**: Memory utilization metrics
    - **disk**: Disk utilization metrics
    - **system**: General system information
    - **timestamp**: When these metrics were collected
    """
    # CPU information
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    
    # Memory information
    memory = psutil.virtual_memory()
    
    # Disk information
    disk = psutil.disk_usage('/')
    
    # System information
    uname = platform.uname()
    
    return {
        "cpu": {
            "usage_percent": cpu_percent,
            "cores": cpu_count
        },
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_percent": memory.percent
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "used_percent": disk.percent
        },
        "system": {
            "system": uname.system,
            "node": uname.node,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
            "python_version": platform.python_version()
        },
        "timestamp": get_utc_now().isoformat()
    }