"""
Consolidated Exception Handling Module

This module consolidates all error handling functionality from:
- app.core.errors
- app.utils.error_utils

Provides consistent error handling across the application with standard error formats,
status codes, and error message conventions.
"""
from fastapi import HTTPException, status, Request
from typing import Optional, Dict, Any, Union, List
from pydantic import BaseModel
import logging

# Configure logger
logger = logging.getLogger(__name__)

# ============================================================================
# Error Response Models
# ============================================================================

class ErrorDetail(BaseModel):
    """Schema for detailed error information"""
    code: str
    message: str
    field: Optional[str] = None

class ErrorResponse(BaseModel):
    """Standard error response schema"""
    status: int
    error: str
    message: str
    request_id: Optional[str] = None
    details: Optional[List[ErrorDetail]] = None
    timestamp: str

# ============================================================================
# Standard Error Types
# ============================================================================

class APIError:
    """Standard API error definitions with status codes and messages"""
    
    # 4xx Client Errors
    BAD_REQUEST = (status.HTTP_400_BAD_REQUEST, "BAD_REQUEST", "Bad request")
    UNAUTHORIZED = (status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "Unauthorized access")
    PAYMENT_REQUIRED = (status.HTTP_402_PAYMENT_REQUIRED, "PAYMENT_REQUIRED", "Payment required")
    FORBIDDEN = (status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Access forbidden")
    NOT_FOUND = (status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Resource not found")
    METHOD_NOT_ALLOWED = (status.HTTP_405_METHOD_NOT_ALLOWED, "METHOD_NOT_ALLOWED", "Method not allowed")
    CONFLICT = (status.HTTP_409_CONFLICT, "CONFLICT", "Resource conflict")
    UNPROCESSABLE_ENTITY = (status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Validation error")
    TOO_MANY_REQUESTS = (status.HTTP_429_TOO_MANY_REQUESTS, "RATE_LIMIT", "Too many requests")
    
    # 5xx Server Errors
    INTERNAL_ERROR = (status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_SERVER_ERROR", "Internal server error")
    NOT_IMPLEMENTED = (status.HTTP_501_NOT_IMPLEMENTED, "NOT_IMPLEMENTED", "Not implemented")
    SERVICE_UNAVAILABLE = (status.HTTP_503_SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE", "Service unavailable")

# ============================================================================
# Core Error Functions
# ============================================================================

def create_error_response(
    error_type: tuple,
    request: Request = None,
    message: str = None,
    details: List[ErrorDetail] = None,
    log_error: bool = True,
) -> Dict[str, Any]:
    """
    Create a standardized error response dictionary.
    
    Args:
        error_type: Tuple of (status_code, error_code, default_message) from APIError class
        request: FastAPI request object (optional)
        message: Custom error message (optional, uses default if not provided)
        details: List of specific error details for validation errors etc.
        log_error: Whether to log this error
        
    Returns:
        Dictionary with standardized error response format
    """
    from app.utils.datetime_utils import get_utc_now
    
    status_code, error_code, default_message = error_type
    error_message = message or default_message
    
    # Create request ID if request is provided
    request_id = None
    if request:
        request_id = getattr(request.state, "request_id", None)
    
    # Create the standardized error response
    error_response = {
        "status": status_code,
        "error": error_code,
        "message": error_message,
        "timestamp": get_utc_now().isoformat()
    }
    
    # Add request ID if available
    if request_id:
        error_response["request_id"] = request_id
    
    # Add error details if provided
    if details:
        error_response["details"] = [detail.dict() for detail in details]
    
    # Log the error if requested
    if log_error:
        log_message = f"Error {status_code} ({error_code}): {error_message}"
        if status_code >= 500:
            logger.error(log_message, exc_info=True)
        else:
            logger.warning(log_message)
    
    return error_response

def raise_http_exception(
    error_type: tuple,
    request: Request = None,
    message: str = None,
    headers: Dict[str, str] = None,
    details: List[ErrorDetail] = None,
    log_error: bool = True
) -> None:
    """
    Raise a standardized HTTP exception with consistent formatting.
    
    Args:
        error_type: Tuple of (status_code, error_code, default_message) from APIError class
        request: FastAPI request object (optional)
        message: Custom error message (optional, uses default if not provided)
        headers: Additional headers to include in response (optional)
        details: List of specific error details (optional)
        log_error: Whether to log this error (default: True)
    
    Raises:
        HTTPException: FastAPI HTTP exception with standardized format
    """
    status_code = error_type[0]
    error_response = create_error_response(
        error_type=error_type,
        request=request,
        message=message,
        details=details,
        log_error=log_error
    )
    
    raise HTTPException(
        status_code=status_code,
        detail=error_response,
        headers=headers
    )

# ============================================================================
# Convenience Functions for Common Error Types
# ============================================================================

def not_found(
    message: str = None, 
    details: List[ErrorDetail] = None,
    request: Request = None
) -> None:
    """
    Raise a 404 Not Found exception.
    
    Args:
        message: Custom error message (optional)
        details: List of specific error details (optional)
        request: FastAPI request object (optional)
    """
    raise_http_exception(APIError.NOT_FOUND, request=request, message=message, details=details)

def unauthorized(
    message: str = None, 
    details: List[ErrorDetail] = None,
    request: Request = None
) -> None:
    """
    Raise a 401 Unauthorized exception.
    
    Args:
        message: Custom error message (optional)
        details: List of specific error details (optional)
        request: FastAPI request object (optional)
    """
    raise_http_exception(APIError.UNAUTHORIZED, request=request, message=message, details=details)

def forbidden(
    message: str = None, 
    details: List[ErrorDetail] = None,
    request: Request = None
) -> None:
    """
    Raise a 403 Forbidden exception.
    
    Args:
        message: Custom error message (optional)
        details: List of specific error details (optional)
        request: FastAPI request object (optional)
    """
    raise_http_exception(APIError.FORBIDDEN, request=request, message=message, details=details)

def bad_request(
    message: str = None, 
    details: List[ErrorDetail] = None,
    request: Request = None
) -> None:
    """
    Raise a 400 Bad Request exception.
    
    Args:
        message: Custom error message (optional)
        details: List of specific error details (optional)
        request: FastAPI request object (optional)
    """
    raise_http_exception(APIError.BAD_REQUEST, request=request, message=message, details=details)

def validation_error(
    errors: List[Dict[str, Any]], 
    message: str = "Validation error", 
    request: Request = None
) -> None:
    """
    Raise a 422 Unprocessable Entity exception for validation errors.
    
    Args:
        errors: List of validation errors
        message: Custom error message (optional)
        request: FastAPI request object (optional)
    """
    # Convert validation errors to ErrorDetail format
    details = []
    for error in errors:
        details.append(ErrorDetail(
            code="VALIDATION_ERROR",
            message=error.get("msg", "Invalid value"),
            field=".".join(str(loc) for loc in error.get("loc", []))
        ))
    
    raise_http_exception(APIError.UNPROCESSABLE_ENTITY, request=request, message=message, details=details)

def internal_error(message: str = None, request: Request = None) -> None:
    """
    Raise a 500 Internal Server Error exception.
    
    Args:
        message: Custom error message (optional)
        request: FastAPI request object (optional)
    """
    raise_http_exception(APIError.INTERNAL_ERROR, request=request, message=message)

def payment_error(
    message: str = None, 
    details: List[ErrorDetail] = None,
    request: Request = None
) -> None:
    """
    Raise a 402 Payment Required exception.
    
    Args:
        message: Custom error message (optional) 
        details: List of specific error details (optional)
        request: FastAPI request object (optional)
    """
    raise_http_exception(APIError.PAYMENT_REQUIRED, request=request, message=message, details=details)

def conflict_error(
    message: str = None,
    details: List[ErrorDetail] = None,
    request: Request = None
) -> None:
    """
    Raise a 409 Conflict exception.
    
    Args:
        message: Custom error message (optional)
        details: List of specific error details (optional)
        request: FastAPI request object (optional)
    """
    raise_http_exception(APIError.CONFLICT, request=request, message=message, details=details)

def rate_limit_error(
    message: str = None,
    details: List[ErrorDetail] = None,
    request: Request = None
) -> None:
    """
    Raise a 429 Too Many Requests exception.
    
    Args:
        message: Custom error message (optional)
        details: List of specific error details (optional)
        request: FastAPI request object (optional)
    """
    raise_http_exception(APIError.TOO_MANY_REQUESTS, request=request, message=message, details=details)

# ============================================================================
# Exception Handler Setup
# ============================================================================

def setup_exception_handlers(app):
    """
    Set up centralized exception handlers for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    from fastapi.exception_handlers import http_exception_handler
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException
    
    @app.exception_handler(StarletteHTTPException)
    async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions with standardized format"""
        return await http_exception_handler(request, exc)
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors with standardized format"""
        validation_error(exc.errors(), request=request)
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions with standardized format"""
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        internal_error(
            message="An unexpected error occurred. Please try again later.",
            request=request
        )

# ============================================================================
# Business Logic Exceptions
# ============================================================================

class BusinessLogicException(Exception):
    """Base exception for business logic errors"""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code or "BUSINESS_LOGIC_ERROR"
        super().__init__(self.message)

class InsufficientCreditsException(BusinessLogicException):
    """Exception for insufficient credits scenarios"""
    def __init__(self, message: str = "Insufficient credits"):
        super().__init__(message, "INSUFFICIENT_CREDITS")

class InvalidTokenException(BusinessLogicException):
    """Exception for invalid token scenarios"""
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message, "INVALID_TOKEN")

class SessionNotActiveException(BusinessLogicException):
    """Exception for inactive session scenarios"""
    def __init__(self, message: str = "Session is not active"):
        super().__init__(message, "SESSION_NOT_ACTIVE")

class SubscriptionExpiredException(BusinessLogicException):
    """Exception for expired subscription scenarios"""
    def __init__(self, message: str = "Subscription has expired"):
        super().__init__(message, "SUBSCRIPTION_EXPIRED")

# ============================================================================
# Backwards Compatibility Aliases
# ============================================================================

# For backward compatibility with existing imports
APIErrorType = APIError
create_standard_error_response = create_error_response
raise_standard_http_exception = raise_http_exception
