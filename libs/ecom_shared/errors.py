"""
Standardized error responses and HTTP exception helpers.

This module provides consistent error handling helpers for FastAPI endpoints.
"""

from typing import Any, Optional, Union

from fastapi import HTTPException, status

from .models import ErrorResponse


def validation_error(
    detail: str = "Invalid input parameters",
    field: Optional[str] = None,
    value: Optional[Any] = None,
) -> HTTPException:
    """
    Create a 422 Unprocessable Entity exception with consistent error structure.

    Args:
        detail: Error message explaining the validation error
        field: Optional field name that failed validation
        value: Optional invalid value provided

    Returns:
        HTTPException with 422 status code and structured error content
    """
    error_msg = detail
    if field:
        error_msg = f"{detail} for field '{field}'"
        if value is not None:
            error_msg += f" with value '{value}'"

    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=ErrorResponse(error="Validation Error", detail=error_msg).model_dump(),
    )


def not_found_error(
    entity_type: str, entity_id: Union[str, int], detail: Optional[str] = None
) -> HTTPException:
    """
    Create a 404 Not Found exception with consistent error structure.

    Args:
        entity_type: Type of entity not found (e.g., "order", "product")
        entity_id: Identifier of the entity not found
        detail: Optional additional details about the error

    Returns:
        HTTPException with 404 status code and structured error content
    """
    error_msg = f"{entity_type.title()} with ID '{entity_id}' not found"
    if detail:
        error_msg += f". {detail}"

    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ErrorResponse(error="Not Found", detail=error_msg).model_dump(),
    )


def service_error(
    message: str = "Internal service error",
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> HTTPException:
    """
    Create a service error exception with consistent structure.

    Args:
        message: Error message explaining the service error
        status_code: HTTP status code to use

    Returns:
        HTTPException with provided status code and structured error content
    """
    return HTTPException(
        status_code=status_code,
        detail=ErrorResponse(error="Service Error", detail=message).model_dump(),
    )


def unauthorized_error(message: str = "Authentication required") -> HTTPException:
    """
    Create a 401 Unauthorized exception with consistent error structure.

    Args:
        message: Error message explaining the authentication error

    Returns:
        HTTPException with 401 status code and structured error content
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=ErrorResponse(error="Unauthorized", detail=message).model_dump(),
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden_error(message: str = "Insufficient permissions") -> HTTPException:
    """
    Create a 403 Forbidden exception with consistent error structure.

    Args:
        message: Error message explaining the permissions error

    Returns:
        HTTPException with 403 status code and structured error content
    """
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=ErrorResponse(error="Forbidden", detail=message).model_dump(),
    )
