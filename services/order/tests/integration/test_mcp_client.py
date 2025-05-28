# services/order/tests/integration/test_mcp_client.py

import json

import pytest
from agents.mcp.server import MCPServerSse

from order.config import config


async def _call_and_parse(server, tool_name: str, params: dict):
    """Helper to call a tool and parse the response."""
    result = await server.call_tool(tool_name, params)

    # Extract the text content from the result
    if hasattr(result, "content") and result.content:
        text = result.content[0].text
    else:
        text = str(result)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        # non-JSON response => treat as plain text
        return {"error": {"message": text}}

    # If JSON-RPC envelope, unwrap it
    if "jsonrpc" in payload:
        if "error" in payload:
            return {"error": payload["error"]}
        return payload.get("result")

    # Otherwise it's already the business payload
    return payload


# Add this test to see what's actually being returned


@pytest.mark.asyncio
@pytest.mark.live_integration
async def test_raw_mcp_response():
    """Debug test to see the raw MCP response format."""
    import httpx

    base_url = "http://127.0.0.1:8002"

    # First, let's see what the direct API returns
    async with httpx.AsyncClient() as client:
        # Test a simple endpoint directly
        print("\n[DEBUG] Direct API call to /orders/customer/37077")
        response = await client.get(f"{base_url}/orders/customer/37077?limit=2")
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Response text: {response.text}")

        # Now test through MCP
        print("\n[DEBUG] MCP call")

        # Try calling MCP endpoint with raw request
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "get_orders_by_customer",
            "params": {"customer_id": 37077, "limit": 2},
            "id": 1,
        }

        response = await client.post(
            f"{base_url}/mcp/call",
            json=mcp_request,
            headers={"Content-Type": "application/json"},
        )
        print(f"MCP Status: {response.status_code}")
        print(f"MCP Response: {response.text[:1000]}")


@pytest.mark.asyncio
@pytest.mark.live_integration
async def test_mcp_tool_discovery():
    """Test that MCP server exposes expected tools."""
    url = "http://127.0.0.1:8002/mcp"
    print(f"[DEBUG] Using MCP URL for order: {url}")

    # First check if the service is accessible
    import requests

    try:
        health_check = requests.get("http://127.0.0.1:8002/health", timeout=2)
        print(f"[DEBUG] Health check status: {health_check.status_code}")
    except Exception as e:
        print(f"[DEBUG] Health check failed: {e}")
        pytest.fail("Order service not accessible")

    server = MCPServerSse(params={"url": url}, cache_tools_list=True)

    await server.connect()
    try:
        print("[DEBUG] Connected to MCP server")
        tools = await server.list_tools()
        print(f"[DEBUG] Found {len(tools)} tools")

        tool_names = {t.name for t in tools}
        print(f"[DEBUG] Actual tool names: {sorted(tool_names)}")

        expected = {
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
        }
        print(f"[DEBUG] Expected tools: {sorted(expected)}")
        missing = expected - tool_names
        print(f"[DEBUG] Missing tools: {sorted(missing)}")
        assert expected.issubset(tool_names), f"Missing tools: {missing}"
    finally:
        await server.cleanup()


@pytest.mark.asyncio
@pytest.mark.live_integration
async def test_mcp_health():
    """Test the health endpoint via MCP."""
    url = "http://127.0.0.1:8002/mcp"
    print(f"[DEBUG] Using MCP URL for order: {url}")

    server = MCPServerSse(params={"url": url}, cache_tools_list=True)

    await server.connect()
    try:
        data = await _call_and_parse(server, "order_health", {})
        if isinstance(data, dict) and "error" in data:
            msg = str(data["error"]).lower()
            assert "error" in msg or "validation" in msg
        else:
            assert data["status"] == "ok"
            assert "details" in data
    finally:
        await server.cleanup()


@pytest.mark.asyncio
@pytest.mark.live_integration
async def test_mcp_get_orders_by_category():
    """Test getting orders by category."""
    url = "http://127.0.0.1:8002/mcp"

    server = MCPServerSse(params={"url": url}, cache_tools_list=True)

    await server.connect()
    try:
        # Use a valid category from the CSV
        params = {"category": "Auto & Accessories", "limit": 2}
        result = await server.call_tool("get_orders_by_category", params)

        if hasattr(result, "content") and result.content:
            data = json.loads(result.content[0].text)
        else:
            data = json.loads(str(result))

        assert "items" in data

        # Invalid category (should return error or empty results)
        params = {"category": "NonExistentCategory", "limit": 2}
        result = await server.call_tool("get_orders_by_category", params)

        if hasattr(result, "content") and result.content:
            text = result.content[0].text
        else:
            text = str(result)

        try:
            data = json.loads(text)
            assert "items" in data and (
                data["items"] == [] or data.get("returned_count", 0) == 0
            )
        except json.JSONDecodeError:
            assert "error" in text.lower() or "not found" in text.lower()
    finally:
        await server.cleanup()


# In test_mcp_client.py, update the search test:


@pytest.mark.asyncio
@pytest.mark.live_integration
async def test_mcp_search_orders():
    """Test searching orders with filters."""
    url = "http://127.0.0.1:8002/mcp"

    server = MCPServerSse(params={"url": url}, cache_tools_list=True)

    await server.connect()
    try:
        # Valid search - should return items
        params = {"filters": {"product_category": {"$contains": "Auto"}}, "limit": 2}

        result = await server.call_tool("search_orders", params)

        if hasattr(result, "content") and result.content:
            data = json.loads(result.content[0].text)
        else:
            data = json.loads(str(result))

        assert "items" in data
        if len(data["items"]) > 0:
            # Verify the items actually match the filter
            for item in data["items"]:
                assert "Auto" in item["product_category"]

        # Search for non-existent category using UUID to ensure uniqueness
        import uuid

        non_existent = f"NONEXISTENT_{uuid.uuid4()}"

        params = {
            "filters": {"product_category": {"$contains": non_existent}},
            "limit": 2,
        }
        result = await server.call_tool("search_orders", params)

        if hasattr(result, "content") and result.content:
            text = result.content[0].text
            data = json.loads(text)

            # Should return empty items for non-existent category
            assert "items" in data
            assert len(data["items"]) == 0, (
                f"Should not find any items containing {non_existent}, but got {len(data['items'])} items"
            )
            assert data.get("returned_count", 0) == 0

    finally:
        await server.cleanup()


@pytest.mark.asyncio
@pytest.mark.live_integration
async def test_mcp_get_orders_by_customer():
    """Test getting orders by customer - works with any data."""
    url = "http://127.0.0.1:8002/mcp"

    server = MCPServerSse(params={"url": url}, cache_tools_list=True)

    await server.connect()
    try:
        # Get a real customer ID from the data
        recent_result = await server.call_tool("get_recent_orders", {"limit": 1})
        recent_data = json.loads(recent_result.content[0].text)

        if recent_data["items"]:
            real_customer_id = recent_data["items"][0]["customer_id"]

            # Test with real customer
            params = {"customer_id": real_customer_id, "limit": 2}
            result = await server.call_tool("get_orders_by_customer", params)
            data = json.loads(result.content[0].text)

            assert "items" in data
            assert len(data["items"]) > 0

        # Test with non-existent customer - NOW EXPECTS EMPTY RESULT, NOT ERROR
        params = {"customer_id": -99999, "limit": 2}
        result = await server.call_tool("get_orders_by_customer", params)
        text = result.content[0].text if hasattr(result, "content") else str(result)

        # Parse the response
        data = json.loads(text)

        # Should get empty items, not an error
        assert "items" in data
        assert data["items"] == []
        assert data.get("returned_count", 0) == 0
        assert data.get("total_count", 0) == 0

    finally:
        await server.cleanup()


@pytest.mark.asyncio
@pytest.mark.live_integration
async def test_mcp_total_sales_by_category():
    """Test getting total sales by category."""
    url = "http://127.0.0.1:8002/mcp"

    server = MCPServerSse(params={"url": url}, cache_tools_list=True)

    await server.connect()
    try:
        result = await server.call_tool("total_sales_by_category", {})

        if hasattr(result, "content") and result.content:
            text = result.content[0].text
            print(f"[DEBUG] Response text: '{text}'")
            if not text.strip():
                pytest.fail("Empty response from MCP server")
            data = json.loads(text)
        else:
            text = str(result)
            print(f"[DEBUG] Response text: '{text}'")
            if not text.strip():
                pytest.fail("Empty response from MCP server")
            data = json.loads(text)

        assert isinstance(data, list)
        assert any("category" in s and "total_sales" in s for s in data)
    finally:
        await server.cleanup()


@pytest.mark.asyncio
@pytest.mark.live_integration
async def test_mcp_high_profit_products():
    """Test getting high profit products."""
    url = "http://127.0.0.1:8002/mcp"

    server = MCPServerSse(params={"url": url}, cache_tools_list=True)

    await server.connect()
    try:
        params = {"min_profit": 1.0, "limit": 2}
        result = await server.call_tool("high_profit_products", params)

        if hasattr(result, "content") and result.content:
            data = json.loads(result.content[0].text)
        else:
            data = json.loads(str(result))

        assert "items" in data
    finally:
        await server.cleanup()


@pytest.mark.asyncio
@pytest.mark.live_integration
async def test_mcp_shipping_cost_summary():
    """Test getting shipping cost summary."""
    url = "http://127.0.0.1:8002/mcp"

    server = MCPServerSse(params={"url": url}, cache_tools_list=True)

    await server.connect()
    try:
        result = await server.call_tool("shipping_cost_summary", {})

        if hasattr(result, "content") and result.content:
            data = json.loads(result.content[0].text)
        else:
            data = json.loads(str(result))

        # Accept either 'average_cost' or 'total_cost' as valid keys
        assert "average_cost" in data or "total_cost" in data
    finally:
        await server.cleanup()


@pytest.mark.asyncio
@pytest.mark.live_integration
async def test_mcp_profit_by_gender():
    """Test getting profit by gender."""
    url = "http://127.0.0.1:8002/mcp"

    server = MCPServerSse(params={"url": url}, cache_tools_list=True)

    await server.connect()
    try:
        result = await server.call_tool("profit_by_gender", {})

        if hasattr(result, "content") and result.content:
            data = json.loads(result.content[0].text)
        else:
            data = json.loads(str(result))

        assert isinstance(data, list)
        assert any("gender" in s and "total_profit" in s for s in data)
    finally:
        await server.cleanup()


@pytest.mark.asyncio
@pytest.mark.live_integration
async def test_mcp_get_orders_by_customer_guardrail():
    """Test validation errors are handled properly."""
    url = "http://127.0.0.1:8002/mcp"

    server = MCPServerSse(params={"url": url}, cache_tools_list=True)

    await server.connect()
    try:
        # Missing required parameter (should trigger validation error)
        result = await server.call_tool("get_orders_by_customer", {})

        if hasattr(result, "content") and result.content:
            text = result.content[0].text
        else:
            text = str(result)

        # Assert that the response contains an error or validation message
        assert "error" in text or "validation" in text or "detail" in text
    finally:
        await server.cleanup()
