# order-service/app.py
from typing import List

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_mcp import FastApiMCP
from libs.ecom_shared.errors import not_found_error, service_error, validation_error
from libs.ecom_shared.guardrails import GuardrailViolation
from libs.ecom_shared.health import format_health_response
from libs.ecom_shared.logging import get_logger
from libs.ecom_shared.models import HealthStatus

from .config import config
from .data_service import OrderDataService
from .models import (
    CategorySalesStats,
    CustomerStats,
    GenderProfitStats,
    OrderItem,
    OrderSearchRequest,
    OrdersResponse,
    ShippingCostSummary,
)

logger = get_logger(__name__)


app = FastAPI(
    title="Order Service",
    description="Order query endpoints and MCP tool exposure",
    version="0.6.0",
)

# Add CORS middleware for Render deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.onrender.com", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_order_service() -> OrderDataService:
    """
    Dependency provider for OrderDataService.
    In tests, this can be overridden to provide a mock service.
    """
    return OrderDataService(config.data_path)


@app.get("/health", tags=["orders"], operation_id="order_health")
async def health(service: OrderDataService = Depends(get_order_service)):
    """
    Service health check endpoint.
    Returns order count and data statistics.
    """
    try:
        stats = service.get_health_stats()
        return format_health_response(
            status=HealthStatus.OK,
            details={
                "order_count": stats["total_orders"],
                "categories": stats["categories"],
                "date_range": stats["date_range"],
            },
            version=app.version,
        )
    except Exception as e:
        logger.error("Health check failed", exc_info=e)
        return format_health_response(
            status=HealthStatus.ERROR,
            details={"error": str(e)},
            version=app.version,
        )


@app.get(
    "/orders/all",
    response_model=OrdersResponse,
    tags=["orders"],
    operation_id="get_all_orders",
)
async def get_all_orders(
    limit: int = 100,
    offset: int = 0,
    service: OrderDataService = Depends(get_order_service),
):
    """
    Retrieve all orders with pagination.

    This endpoint helps you browse through large datasets page by page.

    How to use:
    - First page: offset=0, limit=100 (returns orders 1-100)
    - Second page: offset=100, limit=100 (returns orders 101-200)
    - Third page: offset=200, limit=100 (returns orders 201-300)

    The response includes total_count so you know how many orders exist.

    Args:
        limit: Maximum number of orders per page (capped at 1000 for safety)
        offset: Number of orders to skip (for pagination)

    Returns:
        OrdersResponse with items, total_count, returned_count, limit, and offset
    """
    try:
        # Cap limit for safety
        limit = min(limit, 1000)

        # Get total count
        total_count = len(service.df)

        # Get paginated slice
        orders = service.get_all_orders(limit=limit, offset=offset)

        return OrdersResponse(
            items=orders,
            total_count=total_count,
            returned_count=len(orders),
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error("Error fetching all orders", exc_info=e)
        raise service_error(str(e))


@app.get(
    "/orders/customer/{customer_id}",
    response_model=OrdersResponse,
    tags=["orders"],
    operation_id="get_orders_by_customer",
)
async def get_orders_by_customer(
    customer_id: int,
    limit: int = 10,
    service: OrderDataService = Depends(get_order_service),
):
    """
    Retrieve all orders for a specific customer.

    Args:
        customer_id: The customer ID to search for
        limit: Maximum number of orders to return
        service: OrderDataService dependency

    Returns:
        OrdersResponse containing matching orders
    """
    try:
        orders = service.get_orders_by_customer(customer_id, limit)
        return OrdersResponse(
            items=orders,
            total_count=len(orders),
            returned_count=len(orders),
            limit=limit,
            offset=0,
        )
    except ValueError:
        # Return empty response instead of 404 for non-existent customers
        return OrdersResponse(
            items=[],
            total_count=0,
            returned_count=0,
            limit=limit,
            offset=0,
        )
    except Exception as e:
        logger.error(f"Error fetching orders for customer {customer_id}", exc_info=e)
        raise service_error(str(e))


@app.get(
    "/customers/{customer_id}/stats",
    response_model=CustomerStats,
    tags=["orders"],
    operation_id="get_customer_stats",
)
async def get_customer_stats(
    customer_id: int,
    service: OrderDataService = Depends(get_order_service),
):
    """Get comprehensive statistics for a customer."""
    try:
        return service.get_customer_stats(customer_id)
    except ValueError:
        raise not_found_error("customer", customer_id)


@app.get(
    "/orders/category/{category}",
    response_model=OrdersResponse,
    tags=["orders"],
    operation_id="get_orders_by_category",
)
async def get_orders_by_category(
    category: str,
    limit: int = 10,
    service: OrderDataService = Depends(get_order_service),
):
    """
    Retrieve orders in a specific product category.

    Args:
        category: The product category to search for
        limit: Maximum number of orders to return
        service: OrderDataService dependency

    Returns:
        OrdersResponse containing matching orders
    """
    try:
        orders = service.get_orders_by_category(category, limit)
        return OrdersResponse(
            items=orders,
            total_count=len(orders),
            returned_count=len(orders),
            limit=limit,
            offset=0,
        )
    except ValueError:
        raise not_found_error("category", category)
    except Exception as e:
        logger.error(f"Error fetching orders for category {category}", exc_info=e)
        raise service_error(str(e))


@app.get(
    "/orders/priority/{priority}",
    response_model=OrdersResponse,
    tags=["orders"],
    operation_id="get_orders_by_priority",
)
async def get_orders_by_priority(
    priority: str,
    limit: int = 10,
    service: OrderDataService = Depends(get_order_service),
):
    """
    Retrieve orders with specific priority level.

    Priority levels: High, Medium, Low, Critical

    Args:
        priority: Order priority level (case-insensitive)
        limit: Maximum number of orders to return

    Returns:
        OrdersResponse containing matching orders
    """
    try:
        # The data service already has _apply_filters that can handle this
        filters = {"order_priority": {"$contains": priority}}
        orders = service.search_orders(filters=filters, limit=limit)

        if not orders:
            raise ValueError(f"No orders found with priority '{priority}'")

        return OrdersResponse(
            items=orders,
            total_count=len(orders),
            returned_count=len(orders),
            limit=limit,
            offset=0,
        )
    except ValueError as e:
        raise not_found_error("priority", priority)
    except Exception as e:
        logger.error(f"Error fetching orders for priority {priority}", exc_info=e)
        raise service_error(str(e))


@app.get(
    "/orders/recent",
    response_model=OrdersResponse,
    tags=["orders"],
    operation_id="get_recent_orders",
)
async def get_recent_orders(
    limit: int = 5,
    service: OrderDataService = Depends(get_order_service),
):
    """
    Retrieve the most recent orders.

    Args:
        limit: Maximum number of orders to return
        service: OrderDataService dependency

    Returns:
        OrdersResponse containing most recent orders
    """
    try:
        orders = service.get_recent_orders(limit)
        return OrdersResponse(
            items=orders,
            total_count=len(orders),
            returned_count=len(orders),
            limit=limit,
            offset=0,
        )
    except Exception as e:
        logger.error("Error fetching recent orders", exc_info=e)
        raise service_error(str(e))


@app.post(
    "/orders/search",
    response_model=OrdersResponse,
    tags=["orders"],
    operation_id="search_orders",
)
async def search_orders(
    request: OrderSearchRequest,
    service: OrderDataService = Depends(get_order_service),
):
    """
    Search orders using various filters.

    Args:
        request: Search parameters including filters and sorting
        service: OrderDataService dependency

    Returns:
        OrdersResponse containing matching orders
    """
    try:
        orders = service.search_orders(
            filters=request.filters,
            sort=request.sort,
            limit=request.limit,
        )
        return OrdersResponse(
            items=orders,
            total_count=len(orders),
            returned_count=len(orders),
            limit=request.limit,
            offset=0,
        )
    except ValueError as e:
        raise validation_error(str(e))
    except Exception as e:
        logger.error("Error searching orders", exc_info=e)
        raise service_error(str(e))


@app.get(
    "/orders/total-sales-by-category",
    response_model=List[CategorySalesStats],
    tags=["orders"],
    operation_id="total_sales_by_category",
)
async def total_sales_by_category(
    service: OrderDataService = Depends(get_order_service),
):
    """
    Get total sales for each product category.

    Returns:
        List of dictionaries with category sales data
    """
    try:
        return service.total_sales_by_category()
    except Exception as e:
        logger.error("Error calculating total sales by category", exc_info=e)
        raise service_error(str(e))


@app.get(
    "/orders/high-profit-products",
    response_model=OrdersResponse,
    tags=["orders"],
    operation_id="high_profit_products",
)
async def high_profit_products(
    min_profit: float = 100.0,
    limit: int = 10,
    service: OrderDataService = Depends(get_order_service),
):
    """
    Get orders with profit above specified threshold.

    Args:
        min_profit: Minimum profit threshold
        limit: Maximum number of orders to return
        service: OrderDataService dependency

    Returns:
        OrdersResponse containing high profit orders
    """
    try:
        orders = service.high_profit_products(min_profit, limit)
        return OrdersResponse(
            items=orders,
            total_count=len(orders),
            returned_count=len(orders),
            limit=limit,
            offset=0,
        )
    except ValueError:
        raise not_found_error("order", f"profit > {min_profit}")
    except Exception as e:
        logger.error("Error fetching high profit products", exc_info=e)
        raise service_error(str(e))


@app.get(
    "/orders/shipping-cost-summary",
    response_model=ShippingCostSummary,
    tags=["orders"],
    operation_id="shipping_cost_summary",
)
async def shipping_cost_summary(
    service: OrderDataService = Depends(get_order_service),
):
    """
    Get summary statistics about shipping costs.

    Returns:
        Dictionary with average, min, and max shipping costs
    """
    try:
        return service.shipping_cost_summary()
    except Exception as e:
        logger.error("Error calculating shipping cost summary", exc_info=e)
        raise service_error(str(e))


@app.get(
    "/orders/profit-by-gender",
    response_model=List[GenderProfitStats],
    tags=["orders"],
    operation_id="profit_by_gender",
)
async def profit_by_gender(
    service: OrderDataService = Depends(get_order_service),
):
    """
    Get total profit and order count by customer gender.

    Returns:
        List of dictionaries with gender profit data
    """
    try:
        return service.profit_by_gender()
    except Exception as e:
        logger.error("Error calculating profit by gender", exc_info=e)
        raise service_error(str(e))


# @app.get(
#     "/orders/{order_id}",
#     response_model=OrderItem,
#     tags=["orders"],
#     operation_id="get_order_details",
# )
# async def get_order_details(
#     order_id: str,
#     service: OrderDataService = Depends(get_order_service),
# ):
#     """Get detailed information about a specific order."""
#     try:
#         return service.get_order_details(order_id)
#     except ValueError:
#         raise not_found_error("order", order_id)


@app.exception_handler(GuardrailViolation)
async def guardrail_exception_handler(request: Request, exc: GuardrailViolation):
    """Handle guardrail violations with proper error responses."""
    return JSONResponse(
        status_code=400,
        content={"error": "GuardrailViolation", "detail": str(exc)},
    )


# Mount MCP tools
mcp = FastApiMCP(
    app,
    name="order-service",
    description="Customer order service",
    describe_full_response_schema=True,
    include_tags=["orders"],
    include_operations=[
        "order_health",
        "get_all_orders",
        "get_orders_by_customer",
        # "get_order_details",
        "get_customer_stats",
        "get_orders_by_category",
        "get_orders_by_priority",
        "get_recent_orders",
        "search_orders",
        "total_sales_by_category",
        "high_profit_products",
        "shipping_cost_summary",
        "profit_by_gender",
    ],
)
mcp.mount()
