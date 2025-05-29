# Health check
curl -X GET https://ecom-product-w38k.onrender.com/health | jq .

# Test MCP SSE endpoint
curl -N -H "Accept: text/event-stream" https://ecom-product-w38k.onrender.com/mcp

# Test semantic search
curl -X POST https://ecom-product-w38k.onrender.com/search/semantic \
  -H "Content-Type: application/json" \
  -d '{"query": "wireless headphones", "limit": 5}' | jq .

# Test MCP with JSON
curl -X GET https://ecom-product-w38k.onrender.com/mcp -H "Accept: application/json" | jq .
