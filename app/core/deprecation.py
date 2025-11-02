"""
Deprecation utilities for API endpoints.

Provides decorators and middleware for marking endpoints as deprecated
and redirecting to new endpoints.
"""

import warnings
from functools import wraps
from typing import Callable, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse


class DeprecationWarning(UserWarning):
    """Warning category for deprecated API endpoints."""
    pass


def deprecated_endpoint(
    new_endpoint: str,
    removal_version: Optional[str] = None,
    message: Optional[str] = None,
):
    """
    Decorator to mark an endpoint as deprecated.
    
    Adds deprecation headers to the response and logs warnings.
    
    Args:
        new_endpoint: The new endpoint that should be used instead
        removal_version: Version when this endpoint will be removed
        message: Custom deprecation message
        
    Example:
        @router.get("/old-endpoint")
        @deprecated_endpoint("/new-endpoint", "2.0.0")
        def old_endpoint():
            return {"data": "..."}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build deprecation message
            deprecation_msg = message or f"This endpoint is deprecated. Use {new_endpoint} instead."
            if removal_version:
                deprecation_msg += f" This endpoint will be removed in version {removal_version}."
            
            # Emit warning
            warnings.warn(deprecation_msg, DeprecationWarning, stacklevel=2)
            
            # Call original function
            result = await func(*args, **kwargs) if callable(getattr(func, "__call__", None)) else func(*args, **kwargs)
            
            # If result is a Response, add headers
            if isinstance(result, Response):
                result.headers["X-API-Deprecated"] = "true"
                result.headers["X-API-Deprecation-Info"] = new_endpoint
                if removal_version:
                    result.headers["X-API-Removal-Version"] = removal_version
            
            return result
        
        # Mark the function as deprecated for OpenAPI docs
        wrapper.__deprecated__ = True  # type: ignore
        wrapper.__deprecation_info__ = {  # type: ignore
            "new_endpoint": new_endpoint,
            "removal_version": removal_version,
            "message": message,
        }
        
        return wrapper
    
    return decorator


def add_deprecation_headers(response: Response, new_endpoint: str, removal_version: Optional[str] = None):
    """
    Add deprecation headers to a response.
    
    Useful for manually adding headers without using the decorator.
    """
    response.headers["X-API-Deprecated"] = "true"
    response.headers["X-API-Deprecation-Info"] = f"Use {new_endpoint} instead"
    if removal_version:
        response.headers["X-API-Removal-Version"] = removal_version
    return response


def create_redirect_response(
    new_endpoint: str,
    message: Optional[str] = None,
    status_code: int = 301,
) -> JSONResponse:
    """
    Create a JSON response that indicates redirection to a new endpoint.
    
    Args:
        new_endpoint: The new endpoint to redirect to
        message: Custom message
        status_code: HTTP status code (301 for permanent redirect, 302 for temporary)
        
    Returns:
        JSONResponse with redirect information
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "deprecated": True,
            "message": message or f"This endpoint has been moved to {new_endpoint}",
            "new_endpoint": new_endpoint,
        },
        headers={
            "X-API-Deprecated": "true",
            "X-API-Deprecation-Info": new_endpoint,
            "Location": new_endpoint,
        },
    )
