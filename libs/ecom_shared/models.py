# libs/ecom_shared/models.py
"""
Shared Pydantic models used across all services.
"""

from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

# Generic type for paginated responses
T = TypeVar("T")


class PaginationParams(BaseModel):
    """
    Common pagination parameters model for request pagination.
    """

    limit: int = Field(
        50, ge=1, le=200, description="Maximum number of records to return"
    )
    offset: int = Field(0, ge=0, description="Starting index for pagination")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response template for consistent pagination across services.

    This model can be used by any service that needs to return paginated lists of items.
    The type parameter T represents the model of items being returned.

    When using with large datasets:
    - The endpoint may limit the number per request
    - Use offset to get subsequent pages: offset=0, 100, 200, etc.
    - Check total_count to know when you've reached the end
    - Example: "Show me orders 500-600" → use offset=500, limit=100

    When displaying paginated results:
    - Show a summary first (total count, page info)
    - Display only 5-10 representative examples, not all items
    - Mention how to get more details or navigate pages
    - For "show me orders 500-600", confirm you're showing the correct range

    Example response format:
    "Showing orders 501-600 of 51,290 total orders. Here are some examples from this range:
    [5-10 examples]
    You can request specific pages or search for particular criteria."
    """

    items: List[T] = Field(..., description="List of items in this page")
    total_count: int = Field(..., description="Total number of items across all pages")
    limit: int = Field(..., description="Maximum number of items per page")
    offset: int = Field(..., description="Starting index of this page")


class ErrorResponse(BaseModel):
    """
    Standard error response model used across all services.

    Provides a consistent error format for all API endpoints,
    with a machine-readable error code and human-readable detail message.

    Example:
        {
            "error": "not_found",
            "detail": "Order with ID 'ABC123' not found"
        }
    """

    error: str = Field(..., description="Error code or type")
    detail: Optional[str] = Field(None, description="Human-readable error details")


class HealthStatus(str, Enum):
    """
    Health status enum for health check responses.

    Used in /health endpoints to indicate the operational status of the service.
    """

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


class HealthResponse(BaseModel):
    """
    Standard health check response model for /health endpoints.

    Provides consistent health reporting across all services with
    extensible details for service-specific health information.

    Example:
        {
            "status": "ok",
            "version": "1.0.0",
            "details": {
                "database_connection": "healthy",
                "cache_status": "connected",
                "resource_usage": {
                    "cpu": 0.2,
                    "memory": "45MB"
                }
            }
        }
    """

    status: HealthStatus = Field(..., description="Overall health status")
    version: str = Field(..., description="Service version identifier")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Service-specific health details"
    )


# Common HTTP/JSON standards


class JSONRPCRequest(BaseModel):
    """
    JSON-RPC 2.0 request model for RPC-style API requests.

    Follows the JSON-RPC 2.0 specification for structured remote procedure calls.

    Example:
        {
            "jsonrpc": "2.0",
            "method": "get_order",
            "params": {"order_id": "123"},
            "id": "abc-123"
        }
    """

    jsonrpc: str = Field("2.0", description="JSON-RPC version, always '2.0'")
    method: str = Field(..., description="The RPC method name to call")
    params: Dict[str, Any] = Field(..., description="Parameters for the method call")
    id: Optional[str] = Field(
        None, description="Request identifier for matching responses"
    )


class JSONRPCResponse(BaseModel):
    """
    JSON-RPC 2.0 response model for RPC-style API responses.

    Follows the JSON-RPC 2.0 specification for structured remote procedure call responses.

    Example:
        {
            "jsonrpc": "2.0",
            "result": {"order_id": "123", "status": "shipped"},
            "id": "abc-123"
        }
    """

    jsonrpc: str = Field("2.0", description="JSON-RPC version, always '2.0'")
    result: Any = Field(..., description="The result of the method call")
    id: Optional[str] = Field(
        None, description="Request identifier matching the request"
    )
