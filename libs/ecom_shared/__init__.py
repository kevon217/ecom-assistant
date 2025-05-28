"""
Shared utilities for the ecom-assistant project.

This package provides common utilities, middleware, and models
used across all microservices in the e-commerce assistant.
"""

# Configuration
from .config import BaseServiceConfig

# Context helpers
from .context import AppContext

# Error helpers
from .errors import (
    forbidden_error,
    not_found_error,
    service_error,
    unauthorized_error,
    validation_error,
)

# Guardrails
from .guardrails import (
    GuardrailViolation,
    handle_guardrail_violation,
    input_guard,
    output_guard,
    validate_input,
    validate_output,
)

# Health check
from .health import format_health_response

# Logging
from .logging import get_logger

# Metrics
from .metrics import Metrics

# Middleware
from .middleware import (
    CorrelationIdMiddleware,
    GuardrailMiddleware,
    MetricsMiddleware,
)

# Models
from .models import (
    ErrorResponse,
    HealthResponse,
    HealthStatus,
    JSONRPCRequest,
    JSONRPCResponse,
    PaginatedResponse,
    PaginationParams,
)

__all__ = [
    # Configuration
    "BaseServiceConfig",
    # Context
    "AppContext",
    # Errors
    "validation_error",
    "not_found_error",
    "service_error",
    "unauthorized_error",
    "forbidden_error",
    # Guardrails
    "GuardrailViolation",
    "validate_input",
    "validate_output",
    "handle_guardrail_violation",
    "input_guard",
    "output_guard",
    # Health
    "format_health_response",
    # Logging
    "get_logger",
    # Middleware
    "CorrelationIdMiddleware",
    "MetricsMiddleware",
    "GuardrailMiddleware",
    # Metrics
    "Metrics",
    # Models
    "ErrorResponse",
    "HealthResponse",
    "HealthStatus",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "PaginatedResponse",
    "PaginationParams",
]
