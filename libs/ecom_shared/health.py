# libs/ecom_shared/health.py
"""
Health check utilities for all services.
"""

from typing import Any, Dict

from .models import HealthResponse, HealthStatus


def format_health_response(
    status: HealthStatus, details: Dict[str, Any], version: str
) -> HealthResponse:
    """
    Create a standardized health response.

    Args:
        status: Health status
        details: Service-specific health details
        version: Service version

    Returns:
        Formatted health response
    """
    return HealthResponse(status=status, details=details, version=version)
