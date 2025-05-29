# Health check
curl -X GET https://ecom-chat-itzk.onrender.com/health | jq .

# Debug connections endpoint
curl -X GET https://ecom-chat-itzk.onrender.com/debug/connections | jq .

# Simple chat test
curl -X POST https://ecom-chat-itzk.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, can you help me find products?"}' | jq .

# Streaming chat test
curl -N -X POST https://ecom-chat-itzk.onrender.com/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me wireless headphones under $100"}'
