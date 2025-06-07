from fastapi import FastAPI, APIRouter
from fastapi.openapi.utils import get_openapi
from fastapi.responses import RedirectResponse
import uvicorn
import logging
import atexit

# Import the bcrypt fix before other imports
import app.core.security.bcrypt_fix  # Apply bcrypt compatibility patch

# Import modules from consolidated structure
from app.core.database.db import engine, SessionLocal
from app.core.database.models import create_tables
from app.api.router import api_router
from app.core.config import settings
from app.core.database.migrations import migrate_database
from app.core.middleware import setup_middlewares
from app.core.tasks import setup_scheduler, shutdown_scheduler
from app.utils.rate_limiter import limiter, enhanced_limiter  # Import the rate limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.security.auth import seed_admin_account  # Updated import from consolidated auth module
from app.api.exceptions import create_error_response, APIError, setup_exception_handlers  # Import from consolidated exceptions module
from app.utils.datetime_utils import get_utc_now

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
try:
    create_tables(engine)
    logger.info("Database tables created successfully")
    
    # Run database migrations to update schema if needed
    migrate_database()
    
    # Create initial admin account if none exists
    db = SessionLocal()
    try:
        admin = seed_admin_account(db)
        if admin:
            logger.info(f"Initial admin account created: {admin.username}")
    except Exception as e:
        logger.error(f"Error creating initial admin account: {e}")
    finally:
        db.close()
except Exception as e:
    logger.error(f"Error setting up database: {e}")
    raise

app = FastAPI(
    title="Interview Management Platform API",
    description="""    # Interview Management Platform
    
    A comprehensive platform for managing remote asynchronous interviews with subscription-based access.
    
    ## User Roles
    
    - **Interviewers**: Create interview templates, manage questions, and review candidate responses
    - **Candidates**: Join interview sessions using one-time tokens and submit recorded responses
    - **Administrators**: Manage user accounts, monitor subscription status, and perform system maintenance
    
    ## Core Features
    
    - Subscription management with Stripe integration
    - Secure authentication and role-based access control
    - Interview template creation and management
    - Candidate response recording and transcription
    - Result analysis and reporting    ## API Structure
      - `/api/v1/auth`: Authentication and user management
    - `/api/v1/interviewer`: Interview creation and management
    - `/api/v1/candidates`: Token-based interview access and recording submission
      - `/interviews/access`: Get interview details and verify token
      - `/interviews/start-session`: Start a new interview session
      - `/interviews/complete-session`: Complete the interview session
      - `/interviews/recordings`: Upload interview recordings
    - `/api/v1/billing`: Subscription and payment processing
    - `/api/v1/system`: System health and monitoring
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    terms_of_service="https://example.com/terms/",
)

# The limiter from slowapi doesn't have an init_app method
# Instead, we set it as a state variable on the app
app.state.limiter = limiter
app.state.enhanced_limiter = enhanced_limiter

# Configure exception handler for rate limiting
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    from fastapi.responses import JSONResponse

    # Create a standardized rate limit error response using the consolidated error handling
    error_response = create_error_response(
        error_type=APIError.TOO_MANY_REQUESTS,
        request=request,
        message="Rate limit exceeded. Please try again later.",
    )
    
    # Add rate limit headers to the response
    headers = {
        "Retry-After": str(exc.retry_after),
        "X-RateLimit-Limit": str(exc.limit),
        "X-RateLimit-Reset": str(int(exc.reset_at.timestamp())),
    }
    
    return JSONResponse(
        status_code=429,
        content=error_response,
        headers=headers
    )

# Configure middlewares using the centralized setup function
setup_middlewares(app)

# Set up custom exception handlers
setup_exception_handlers(app)

# Add the SlowAPI middleware for rate limiting
app.add_middleware(SlowAPIMiddleware)

# Include API router with appropriate prefix
app.include_router(api_router, prefix="/api/v1")  # Add API versioning

# Root path redirects to API documentation
@app.get("/", include_in_schema=False)
def root_redirect():
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
        "AdminAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Admin JWT token obtained from /api/v1/admin/auth/login"
        }
    }
    
    # Apply security requirement to specific paths
    if "paths" in openapi_schema:
        for path in openapi_schema["paths"]:
            # Skip login endpoints and public endpoints
            if "/auth/login" in path or "/admin/auth" in path or "/system" in path or "/candidates/verify" in path:
                continue
                
            # Apply appropriate auth to endpoints
            for method in openapi_schema["paths"][path]:
                if openapi_schema["paths"][path][method].get("tags") and \
                   "Admin" in openapi_schema["paths"][path][method].get("tags", []):
                    # Admin endpoints use Admin JWT Auth
                    openapi_schema["paths"][path][method]["security"] = [{"AdminAuth": []}]
                else:
                    # Other protected endpoints use Bearer Auth
                    openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]    # Add API tags with descriptions - these should match tags used in router.py
    openapi_schema["tags"] = [
        {
            "name": "User",
            "description": "User authentication, registration, and account management"
        },
        {
            "name": "Admin",
            "description": "Admin authentication, system management, monitoring, and user administration"
        },
        {
            "name": "Interviewer Panel",
            "description": "Interview creation, question management, token generation, results viewing, and profile settings"
        },        
        {   
            "name": "Candidate Portal",
            "description": "Token-based interview access API with unified endpoints for interview access, session management, and recording submission. Use the /interviews/start-session endpoint to start a session and /interviews/complete-session to complete it. All candidate interactions require a valid token."
        },
        {
            "name": "Billing",
            "description": "Subscription management and payment processing"
        }
    ]
    
    # Organize tags in a logical order for display in UI
    openapi_schema["x-tagGroups"] = [
        {
            "name": "Platform Access",
            "tags": ["User", "Admin"]
        },
        {
            "name": "Core Platform",
            "tags": ["Interviewer Panel", "Candidate Portal"]
        },
        {
            "name": "Platform Operations",
            "tags": ["Billing"]
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Set up background task scheduler
@app.on_event("startup")
def start_scheduler():
    """Start the background task scheduler when the application starts."""
    setup_scheduler()

# Register shutdown function to properly close the scheduler
atexit.register(shutdown_scheduler)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
