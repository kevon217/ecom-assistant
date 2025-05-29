#!/usr/bin/env bash
set -e

echo "🚀 Starting Chat Service..."
echo "📍 ORDER_MCP_URL: $ORDER_MCP_URL"
echo "📍 PRODUCT_MCP_URL: $PRODUCT_MCP_URL"

# Wait on Order MCP (tools discovery)
# until curl -sf "$ORDER_MCP_URL" -H "Accept: application/json"; do
#   echo "⏳ Waiting on Order MCP…"
#   sleep 5
# done

# # Wait on Product MCP (tools discovery)
# until curl -sf "$PRODUCT_MCP_URL" -H "Accept: application/json"; do
#   echo "⏳ Waiting on Product MCP…"
#   sleep 5
# done

# echo "✅ All MCP endpoints ready; launching Chat"

exec uvicorn chat.app:app --host 0.0.0.0 --port ${PORT:-10000}
