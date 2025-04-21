"""
System health and status endpoints.
Provides monitoring and API information endpoints.
"""
from fastapi import APIRouter
from typing import Dict, Any
from app.utils.datetime_utils import get_utc_now

# Create router
system_router = APIRouter()

@system_router.get("/", 
    summary="API Root", 
    description="Root endpoint with API information",
    response_model=Dict[str, str])
def read_root():
    """
    Root endpoint providing basic API information.
    
    Returns:
    - **message**: API status message
    - **documentation**: URL path to API documentation
    - **version**: Current API version
    """
    return {
        "message": "Interview App API is running",
        "documentation": "/docs",
        "version": "1.0.0"
    }

@system_router.get("/status", 
    summary="API Status", 
    description="Detailed API status information",
    response_model=Dict[str, Any])
def api_status():
    """
    Endpoint showing detailed API status and database information.
    
    Returns:
    - **status**: Current API operational status
    - **api_version**: API version number
    - **database**: Database connection status
    - **server_time**: Current server time in ISO format
    """
    return {
        "status": "online",
        "api_version": "1.0.0",
        "database": "connected",
        "server_time": get_utc_now().isoformat()
    }

@system_router.get("/health", 
    summary="Health Check", 
    description="Simple health check endpoint for monitoring",
    response_model=Dict[str, str])
def health_check():
    """
    Health check endpoint for monitoring systems.
    
    This endpoint is designed to be used by load balancers, monitoring tools,
    and container orchestration systems to verify the API is operational.
    
    Returns:
    - **status**: OK if the API is running properly
    """
    return {"status": "ok"}