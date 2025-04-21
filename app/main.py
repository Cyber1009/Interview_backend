from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.openapi.utils import get_openapi
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import uvicorn
import logging
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio

# Import the bcrypt fix before other imports
import app.core.security.bcrypt_fix  # Apply bcrypt compatibility patch

# Import modules from consolidated structure
from app.core.database.db import get_db, engine
from app.core.database.models import create_tables
from app.api.router import api_router
from app.schemas.auth_schemas import Token  # Import Token schema from auth_schemas
from app.core.config import settings
from app.core.security.auth import get_current_user, authenticate_user, create_access_token
from app.core.database.migrations import migrate_database  # Import the migration function
from app.utils.datetime_utils import get_utc_now, safe_compare_dates  # Import datetime utilities
from app.utils.subscription_utils import sync_all_subscription_statuses

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
try:
    create_tables(engine)
    logger.info("Database tables created successfully")
    
    # Run database migrations to update schema if needed
    migrate_database()
except Exception as e:
    logger.error(f"Error setting up database: {e}")
    raise

app = FastAPI(
    title="Interview Management Platform API",
    description="""
    # Interview Management Platform
    
    This API powers an interview management platform that enables:
    
    - **Interviewers**: Create and manage interview templates, questions, and review candidate responses
    - **Candidates**: Join interviews using one-time tokens and submit recorded responses to questions
    - **Administrators**: Manage user accounts, subscription status, and system maintenance
    
    ## Main features
    
    - Complete interview management for remote asynchronous interviews
    - Secure access with token-based authentication
    - Integration with Stripe for subscription management
    - Audio recording uploads with automatic transcription
    
    ## Key endpoints by user role
    
    ### Interviewers
    - `/api/v1/auth/login`: Authentication endpoint
    - `/api/v1/interviewer/interviews`: Create and manage interviews
    - `/api/v1/interviewer/profile`: User profile and theme customization
    
    ### Candidates
    - `/api/v1/candidates`: Session management and recording submission
    
    ### Administrators
    - `/api/v1/admin`: System management functions
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    terms_of_service="https://example.com/terms/",
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router with appropriate prefix
app.include_router(api_router, prefix="/api/v1")  # Add API versioning

# Keep the root path for backward compatibility
@app.get("/", include_in_schema=False)
def legacy_root():
    """Redirect to the API documentation for better user experience"""
    return RedirectResponse(url="/docs")

# Custom OpenAPI schema generator to add more metadata
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add API key security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter the JWT token in the format: Bearer {token}"
        },
        "BasicAuth": {
            "type": "http",
            "scheme": "basic",
            "description": "Basic authentication for admin endpoints"
        }
    }
    
    # Apply security requirement to specific paths
    if "paths" in openapi_schema:
        for path in openapi_schema["paths"]:
            # Skip login endpoints and public endpoints
            if "/auth/login" in path or "/system" in path or "/candidates/verify" in path:
                continue
                
            # Apply Bearer Auth to most endpoints
            for method in openapi_schema["paths"][path]:
                if openapi_schema["paths"][path][method].get("tags") and \
                   "Administration" in openapi_schema["paths"][path][method].get("tags", []):
                    # Admin endpoints use Basic Auth
                    openapi_schema["paths"][path][method]["security"] = [{"BasicAuth": []}]
                else:
                    # Other protected endpoints use Bearer Auth
                    openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]

    # Add API tags with descriptions
    openapi_schema["tags"] = [
        {
            "name": "Authentication",
            "description": "Endpoints for user login, registration, and account management"
        },
        {
            "name": "Interviewer",
            "description": "Endpoints for interviewers to create and manage interviews, questions, tokens, and view results"
        },
        {
            "name": "Candidates",
            "description": "Endpoints for interview participants to join sessions and submit recordings"
        },
        {
            "name": "Administration",
            "description": "Administrative endpoints for system maintenance and user account management"
        },
        {
            "name": "Payments",
            "description": "Subscription and payment management"
        },
        {
            "name": "System",
            "description": "System health and status endpoints"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
