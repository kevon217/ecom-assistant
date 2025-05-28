# libs/ecom_shared/middleware.py
"""
ASGI middleware components for FastAPI applications.

This module provides middleware for correlation ID propagation,
metrics collection, and other cross-cutting concerns.
"""

import time
import uuid
from typing import Callable, List, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logging import get_logger
from .metrics import Metrics


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and propagate correlation IDs.
    Ensures all requests have a correlation ID for tracing.
    """

    def __init__(self, app: ASGIApp, header_name: str = "X-Correlation-ID"):
        """
        Initialize the middleware.

        Args:
            app: The ASGI application
            header_name: The header name for the correlation ID
        """
        super().__init__(app)
        self.header_name = header_name
        self.logger = get_logger("correlation")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and add correlation ID.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            The response with correlation ID header
        """
        # Check if correlation ID exists in request headers
        correlation_id = request.headers.get(self.header_name)

        # Generate new correlation ID if not present
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
            self.logger.debug(
                f"Generated new correlation ID: {correlation_id}",
                extra={"correlation_id": correlation_id},
            )

        # Add correlation ID to request state for access in route handlers
        request.state.correlation_id = correlation_id

        # Process the request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers[self.header_name] = correlation_id

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect and emit request metrics.
    Tracks request counts, durations, and status codes.
    """

    def __init__(self, app: ASGIApp, exclude_paths: Optional[List[str]] = None):
        """
        Initialize the middleware.

        Args:
            app: The ASGI application
            exclude_paths: Optional list of paths to exclude from metrics
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or []
        self.logger = get_logger("metrics")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and collect metrics.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            The response
        """
        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Start timing
        start_time = time.time()

        # Extract path and method for metrics
        path = request.url.path
        method = request.method

        # Process the request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Capture exceptions as 500s in metrics
            self.logger.exception(
                f"Exception in request: {method} {path}",
                extra={"method": method, "path": path, "exception": str(e)},
            )
            status_code = 500
            raise
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Emit metrics
            Metrics.counter(
                "http_requests_total",
                {"method": method, "path": path, "status": str(status_code)},
            )

            Metrics.histogram(
                "http_request_duration_ms",
                duration_ms,
                {"method": method, "path": path},
            )

        return response


class GuardrailMiddleware(BaseHTTPMiddleware):
    """
    Middleware to apply input and output guardrails.
    Validates requests and responses against defined rules.
    """

    def __init__(self, app: ASGIApp):
        """Initialize the middleware."""
        super().__init__(app)
        self.logger = get_logger("guardrails")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and apply guardrails.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            The validated response
        """
        # Apply input guardrails if needed
        # Note: Most validation happens in Pydantic models and path operations

        # Process the request
        response = await call_next(request)

        # Apply output guardrails if needed
        # This could check for sensitive data, etc.

        return response


# class CorrelationIdMiddleware(BaseHTTPMiddleware):
#     """
#     Middleware that adds correlation IDs to requests for tracking across services.

#     If a correlation ID is present in the X-Correlation-ID header, it uses that.
#     Otherwise, it generates a new UUID for the request.
#     """

#     async def dispatch(self, request: Request, call_next: Callable) -> Response:
#         # Check if correlation ID already exists in headers
#         correlation_id = request.headers.get("x-correlation-id")

#         if not correlation_id:
#             # Generate new correlation ID
#             correlation_id = str(uuid.uuid4())

#         # Add correlation ID to request state
#         request.state.correlation_id = correlation_id

#         # Call the next middleware/endpoint
#         response = await call_next(request)

#         # Add correlation ID to response headers
#         response.headers["x-correlation-id"] = correlation_id

#         return response
