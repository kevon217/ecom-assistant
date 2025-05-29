# Health check
curl -X GET https://ecom-order.onrender.com/health | jq .

# Test MCP SSE endpoint (should stream SSE data)
curl -N -H "Accept: text/event-stream" https://ecom-order.onrender.com/mcp

# Test a specific endpoint
curl -X GET "https://ecom-order.onrender.com/orders/customer/12345?limit=5" | jq .

# Test MCP endpoint with regular JSON (to see tool list)
curl -X GET https://ecom-order.onrender.com/mcp -H "Accept: application/json" | jq .
