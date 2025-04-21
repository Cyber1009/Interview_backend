"""
Error handling utilities for standardized API error responses.

This module provides consistent error handling across the application,
with standard error formats, status codes, and error message conventions.
"""
from fastapi import HTTPException, status
from typing import Optional, Dict, Any, Union


class APIError:
    """
    Standard error classes with appropriate status codes and default messages.
    """
    # 400 series - client errors
    BAD_REQUEST = (status.HTTP_400_BAD_REQUEST, "Bad request")
    UNAUTHORIZED = (status.HTTP_401_UNAUTHORIZED, "Authentication required")
    PAYMENT_REQUIRED = (status.HTTP_402_PAYMENT_REQUIRED, "Payment required")
    FORBIDDEN = (status.HTTP_403_FORBIDDEN, "Not authorized to perform this action")
    NOT_FOUND = (status.HTTP_404_NOT_FOUND, "Resource not found")
    METHOD_NOT_ALLOWED = (status.HTTP_405_METHOD_NOT_ALLOWED, "Method not allowed")
    CONFLICT = (status.HTTP_409_CONFLICT, "Resource conflict")
    GONE = (status.HTTP_410_GONE, "Resource no longer available")
    PRECONDITION_FAILED = (status.HTTP_412_PRECONDITION_FAILED, "Precondition failed")
    PAYLOAD_TOO_LARGE = (status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Payload too large")
    UNPROCESSABLE_ENTITY = (status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation error")
    TOO_MANY_REQUESTS = (status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests")
    
    # 500 series - server errors
    INTERNAL_ERROR = (status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error")
    NOT_IMPLEMENTED = (status.HTTP_501_NOT_IMPLEMENTED, "Not implemented")
    SERVICE_UNAVAILABLE = (status.HTTP_503_SERVICE_UNAVAILABLE, "Service unavailable")


def raise_http_exception(
    error_type: tuple,
    detail: str = None,
    headers: Dict[str, str] = None,
    data: Dict[str, Any] = None
) -> None:
    """
    Raise a standardized HTTP exception with consistent formatting.
    
    Args:
        error_type: Tuple of (status_code, default_message) from APIError class
        detail: Custom error message (optional, uses default if not provided)
        headers: Additional headers to include in response (optional)
        data: Additional structured data for the error response (optional)
    
    Raises:
        HTTPException: FastAPI HTTP exception with standardized format
    """
    status_code, default_message = error_type
    
    # Create the error response
    error_detail = {
        "error": {
            "code": status_code,
            "message": detail or default_message,
        }
    }
    
    # Add additional data if provided
    if data:
        error_detail["error"]["data"] = data
    
    raise HTTPException(
        status_code=status_code,
        detail=error_detail,
        headers=headers
    )


def not_found(resource_type: str, resource_id: Union[str, int] = None) -> None:
    """
    Raise a 404 Not Found exception with a standardized message format.
    
    Args:
        resource_type: Type of resource that wasn't found (e.g., "User", "Interview")
        resource_id: Identifier of the resource (optional)
    """
    message = f"{resource_type} not found"
    if resource_id:
        message = f"{resource_type} with ID {resource_id} not found"
    
    raise_http_exception(APIError.NOT_FOUND, detail=message)


def unauthorized(message: str = None) -> None:
    """
    Raise a 401 Unauthorized exception.
    
    Args:
        message: Custom error message (optional)
    """
    headers = {"WWW-Authenticate": "Bearer"}
    raise_http_exception(APIError.UNAUTHORIZED, detail=message, headers=headers)


def forbidden(message: str = None) -> None:
    """
    Raise a 403 Forbidden exception.
    
    Args:
        message: Custom error message (optional)
    """
    raise_http_exception(APIError.FORBIDDEN, detail=message)


def bad_request(message: str = None, data: Dict[str, Any] = None) -> None:
    """
    Raise a 400 Bad Request exception.
    
    Args:
        message: Custom error message (optional)
        data: Additional structured error data (optional)
    """
    raise_http_exception(APIError.BAD_REQUEST, detail=message, data=data)


def internal_error(message: str = None) -> None:
    """
    Raise a 500 Internal Server Error exception.
    
    Args:
        message: Custom error message (optional)
    """
    raise_http_exception(APIError.INTERNAL_ERROR, detail=message)


def payment_error(message: str = None, data: Dict[str, Any] = None) -> None:
    """
    Raise a 402 Payment Required exception.
    
    Args:
        message: Custom error message (optional)
        data: Additional payment error data (optional)
    """
    raise_http_exception(APIError.PAYMENT_REQUIRED, detail=message, data=data)