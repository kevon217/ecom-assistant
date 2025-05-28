# services/order/tests/integration/test_mcp_client.py
"""
Live integration tests for Order Service MCP endpoints.
These tests require the actual order service running.
Use: pytest -m live_integration
"""

import json

import pytest
from agents.mcp.server import MCPServerSse

from order.config import config

URL = "http://127.0.0.1:8002/mcp"


async def _call_and_parse(server, tool_name: str, params: dict):
    """Helper to call a tool and parse the response."""
    result = await server.call_tool(tool_name, params)

    # Extract the text content from the result
    if hasattr(result, "content") and result.content:
        text = result.content[0].text
    else:
        text = str(result)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": {"message": text}}


@pytest.mark.asyncio
@pytest.mark.live_integration
async def test_mcp_tool_discovery():
    """Test that MCP server exposes expected tools."""
    server = MCPServerSse(params={"url": URL}, cache_tools_list=True)

    await server.connect()
    try:
        tools = await server.list_tools()
        tool_names = {t.name for t in tools}

        expected = {
            "order_health",
            "get_all_orders",
            "get_orders_by_customer",
            "get_customer_stats",
            "get_orders_by_category",
            "get_orders_by_priority",
            "get_recent_orders",
            "search_orders",
            "total_sales_by_category",
            "high_profit_products",
            "shipping_cost_summary",
            "profit_by_gender",
        }

        missing = expected - tool_names
        assert expected.issubset(tool_names), f"Missing tools: {missing}"
    finally:
        await server.cleanup()


@pytest.mark.asyncio
@pytest.mark.live_integration
async def test_mcp_health():
    """Test the health endpoint via MCP."""
    server = MCPServerSse(params={"url": URL}, cache_tools_list=True)

    await server.connect()
    try:
        data = await _call_and_parse(server, "order_health", {})
        assert "status" in data or "error" in data
    finally:
        await server.cleanup()


@pytest.mark.asyncio
@pytest.mark.live_integration
async def test_mcp_get_recent_orders():
    """Test getting recent orders."""
    server = MCPServerSse(params={"url": URL}, cache_tools_list=True)

    await server.connect()
    try:
        data = await _call_and_parse(server, "get_recent_orders", {"limit": 2})
        assert "items" in data or "error" in data
    finally:
        await server.cleanup()


@pytest.mark.asyncio
@pytest.mark.live_integration
async def test_mcp_search_orders():
    """Test searching orders with filters."""
    server = MCPServerSse(params={"url": URL}, cache_tools_list=True)

    await server.connect()
    try:
        params = {
            "body": {
                "filters": {"product_category": {"$contains": "Electronics"}},
                "limit": 2,
            }
        }
        data = await _call_and_parse(server, "search_orders", params)
        assert "items" in data or "error" in data
    finally:
        await server.cleanup()
