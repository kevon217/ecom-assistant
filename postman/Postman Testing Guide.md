# Postman Testing Guide

This guide provides instructions for testing the E-Commerce Assistant system using the provided Postman collection.

## Setup

### Import Collection

1. Open Postman Desktop (recommended for SSE streaming support)
2. Import `ecom_assistant_postman_collection.json`
3. The collection "E-Commerce Assistant - Complete Challenge & Demo Collection" will appear

### Environment File Setup

The collection automatically validates required environment variables. Import the appropriate environment file based on your deployment:

#### Local Testing

1. Import `ecom_assistant_local_env.json`
2. Ensure all services are running on specified ports:
   - Chat Service: `http://localhost:8001`
   - Order Service: `http://localhost:8002`
   - Product Service: `http://localhost:8003`
3. No additional configuration needed

#### Render Deployment

1. Import `ecom_assistant_render_env.json`
2. **Update the URLs** with your actual Render service endpoints:

   ```json
   "chat_url": "https://ecom-chat-itzk.onrender.com"
   "order_url": "https://ecom-order.onrender.com"
   "product_url": "https://ecom-product-w38k.onrender.com"
   ```

3. Select the environment before running tests

**Environment Validation**: The collection automatically validates that required variables are set. If you see "Missing environment variables" in the console, double-check your environment selection and variable values.

### Verify System Health

Run the "Health & Discovery" folder first to ensure all services are operational:

- Chat service health check
- Product service with ChromaDB status
- Order service with dataset validation
- MCP integration verification

## Running Tests

### Using Collection Runner

1. **Select what to run**:
   - Entire collection for full validation
   - Individual folders for targeted testing
   - Single requests for debugging

2. **Choose your environment**: Select "Local" or "Render" from the dropdown

3. **Configure Runner Settings**:
   - **Iterations**: Set to `1` (tests are designed for single execution)
   - **Delay**: Set to `500ms` between requests (prevents overwhelming services)
   - **Data**: Leave empty (tests are self-contained)
   - **Persist responses for a session**: ✅ **Enable this**
   - **Save responses**: ✅ **Enable this**

4. **Advanced Settings**:
   - **Stop on first test script error**: Leave unchecked (tests handle errors gracefully)
   - **Keep variable values**: ✅ **Enable this** (maintains session continuity)

5. Click **"Run Collection"**

### Collection Runner Best Practices

**For Full Validation** (recommended):

```
Selection: Entire Collection
Iterations: 1
Delay: 500ms
Persist responses: ✅ Enabled
Save responses: ✅ Enabled
Estimated time: 25-30 minutes
```

**For Quick Health Check**:

```
Selection: 🏥 Health & Discovery folder only
Iterations: 1
Delay: 200ms
Estimated time: 2-3 minutes
```

**For Challenge Requirements Only**:

```
Selection: 🎯 Challenge Requirement Tests folder
Iterations: 1
Delay: 500ms
Estimated time: 10-12 minutes
```

### Expected Results

- **Local Development**: 98%+ pass rate (pagination test may vary based on LLM behavior)
- **Render Deployment**: 95%+ pass rate (account for cold starts and data availability)
- **First-time setup**: 90%+ pass rate (ChromaDB may need initialization)

**Known Variations**:

- Pagination tests depend on LLM interpretation and may show different response formats
- Multi-turn tests require full folder execution to maintain context

**What "Pass" Means**:

- ✅ Green tests: Feature working as expected
- ⚠️ Yellow warnings: Acceptable issues (missing test data, cold starts)
- ❌ Red failures: Actual problems requiring attention

### Exporting Results

After running the collection:

1. **Click "Export Results"** in the runner
2. **Choose JSON format** for detailed debugging data
3. **Save the file** for sharing or analysis

The JSON export includes:

- Full request/response data for every test
- Console logs from test scripts
- Detailed assertion results and failures
- Response times and performance metrics

## Collection Structure

### 1. 🏥 Health & Discovery

- **All Services Health Check**: Verifies chat service is operational
- **Product Service Health**: Checks ChromaDB status (expects ~5k products when ready)
- **Order Service Health**: Validates order dataset (~51k orders)
- **MCP Integration Verification**: Tests MCP tool access via chat interface

### 2. 🎯 Challenge Requirement Tests

#### Order Dataset Queries Simple (5 tests)

- Customer order details (37077)
- High-priority orders
- Order status inquiry (41066)
- Customer total spending
- Recent orders overview

#### Multi-Turn Order Details Flow

Tests realistic multi-turn conversations where users provide information incrementally:

- Initial query without customer ID
- Agent requests clarification
- User provides customer ID
- Agent delivers order details

#### Product Dataset Queries Simple (5 tests)

- Top-rated guitar products
- Thin guitar strings recommendation
- BOYA microphone for cello analysis
- User preference-based search
- Category/brand discovery

#### Cell Phone Order Status Flow

Complex 3-turn conversation demonstrating:

- Information gathering across multiple turns
- Disambiguation when multiple orders exist
- Context retention throughout the conversation

**Reminder**: Multi-turn tests require running the full folder or collection to maintain session context. Individual request execution will not preserve conversation state.

### 3. 💬 Chat Multi-Query Workflows

- **Setup Advanced Session**: Creates session for complex demos
- **Multi-Tool Orchestration**: Single request triggering 3+ service calls
- **Streaming Multi-Tool Execution**: Real-time SSE with tool transparency
- **Comprehensive Business Report**: Enterprise-level multi-service queries

### 4. 🚀 Chat Order Pagination Flow

Demonstrates LLM's ability to handle large datasets with pagination:

- **First Page of Orders**: Tests initial request for all orders (returns information on first 100 of ~51k)
- **Next Page Request**: Verifies LLM can request subsequent pages using offset
- **Specific Range Request**: Tests natural language "show me orders 500-600" translation

This flow validates:

- Understanding of total dataset size
- Correct offset/limit parameter calculation
- Stateful conversation maintenance
- User-friendly presentation of large result sets

**Note**: The LLM may handle pagination differently than expected. It might:

- Show a sample of orders rather than full pages
- Mention total count without explicit "page X of Y" format
- Correctly use API pagination while presenting data differently

This is acceptable behavior as long as:

- The total dataset size is mentioned (~51k orders)
- The LLM can navigate to different pages when asked
- The underlying API calls use correct offset/limit parameters

### 5. 📦 Order Service Tests

**Business Analytics Endpoints**:

- High profit products analysis
- Profit by gender demographics
- Customer lifetime analytics

**Production Safety Features**:

- 51k dataset safety limits
- LLM field exclusion verification

### 6. 🛍️ Product Service Tests

**Semantic Search Capabilities**:

- Basic semantic search with ChromaDB
- Complex filtered searches with multiple constraints

**Note**: ChromaDB unfortunately doesn't employ fuzzy text search match so text filters much be EXACT match. Hence I opted for lowercasing key fields in data preprocesing step before ChromaDB upserting. Future iterations would adopt more robust data preprocessing, handling, and vector database solutions. It's important for LLM to be delivered data that's not artificially lowercased since certain edge cases may require proper capitalization.

**Metadata Discovery**:

- Available brands/stores discovery
- Category discovery for dynamic UIs

**Note**: Lowercasing everything was quick fix to address ChromaDB exact filters. So stores and categories will appear lowercased.

### 7. 🚨 Edge Cases & Resilience

- Non-existent order error handling
- Graceful AI responses to empty results
- Massive data request protection
- Non-existent category search handling
- Input validation testing

### 8. 📊 Performance Benchmarks

- Simple query performance (<1s local, <5s Render)
- Complex multi-tool performance (<20s local, <45s Render)

## Key Test Scenarios

### Multi-Turn Conversations

**Location**: Challenge Requirement Tests → Multi-Turn Order Details Flow & Cell Phone Order Status Flow

These tests validate realistic conversation patterns:

- Users don't always provide complete information upfront
- The assistant asks for clarification when needed
- Context is maintained across multiple exchanges
- Complex scenarios like disambiguation are handled gracefully

**Reminder**: Run these flows completely, not individual requests, to test session management.

### Order Pagination

**Location**: Chat Multi-Query Workflows → Chat Order Pagination Flow

Tests the LLM's ability to:

- Understand large dataset constraints (~51k orders)
- Navigate using pagination (offset/limit)
- Translate natural language requests ("next 100", "orders 500-600")
- Present data without overwhelming users

### Multi-Tool Orchestration

**Location**: Chat Multi-Query Workflows → "Multi-Tool: Order + Analytics + Gender"

Single request that triggers multiple service calls:

```
"Hey can you get my order 37077 and also tell me what are the high profit products and profit by gender analysis?"
```

**Expected**: The AI synthesizes data from order lookup, profit analysis, and demographic analytics into a comprehensive response.

### Session Continuity

Tests maintain conversation context using session IDs:

- Simple queries establish and reuse sessions within their workflow
- Multi-turn flows demonstrate complex session management
- Pagination tests show stateful navigation through large datasets

### Streaming Responses

**Location**: Chat Multi-Query Workflows → "Streaming Multi-Tool Execution"

For SSE endpoints, use the **Raw** view in Postman to see streaming events:

```
data: {"type": "tool_start", "tool": "semantic_search", "message": "🔧 Searching..."}
data: {"type": "content", "content": "I found several products..."}
data: {"type": "tool_end", "tool": "semantic_search", "message": "✓ Complete"}
data: {"type": "done"}
```

### Production Safety

**Location**: Order Service Tests → "51k Dataset Safety Limit"

Tests automatic limiting of large datasets:

- ~51k total orders in system
- Automatic cap at 1,000 records per request (though LLM is currently instructed to output much less)
- Prevents LLM token overflow

## Viewing Results

### Response Formats

- **JSON Responses**: Use "Pretty" view for formatted chat responses
- **SSE Streaming**: Use "Raw" view for streaming endpoints
- **Console Output**: Check Postman Console (View → Show Postman Console) for detailed test logs

### Session Management

The collection automatically manages sessions:

- Session IDs are generated and reused within test workflows
- Each major workflow section gets its own session
- Multi-turn conversations require sequential execution
- No manual session management required

## Troubleshooting

### Common Issues

**"Missing environment variables" error**:

- Ensure you've selected the correct environment
- Verify all three URL variables are set

**Multi-turn tests failing**:

- These must be run as a complete folder, not individual requests
- Session context is lost when running requests individually
- Use Collection Runner for proper execution

**ChromaDB not ready**:

- Tests will pass but note the unavailable status
- Run your bootstrap script to initialize the vector database
- Re-run tests after initialization

**Slow response times on Render**:

- First requests may take 30+ seconds due to cold starts
- Subsequent requests should be faster
- Tests automatically account for this with extended timeouts

**Order tests showing empty results**:

- This is expected behavior - the system returns empty lists for non-existent data
- Tests verify the AI responds appropriately with "no results found" messages

**Pagination tests showing longer times**:

- First pagination request may take 30-70 seconds
- This is due to the LLM processing how to present large datasets
- Subsequent pagination requests should be faster (10-15 seconds)

**Pagination test variations**:

- Different LLMs may present paginated data differently
- Some show explicit "page 1 of X" format, others show samples
- Both approaches are valid if they mention total count and support navigation
- Consider adjusting test expectations based on your LLM's behavior

**Order ID confusion in responses**:

- The LLM may confuse customer_id with order_id in responses (order_id is UUID added to each unique record during data preprocessing)
- The underlying data model correctly excludes order_id from LLM visibility (Pydantic model field setting: exclude=True)

**Streaming tests timeout**:

- Ensure you're using Postman Desktop (better SSE support)
- Check that your chat service is responding
- Large streaming responses are automatically truncated for testing

### Performance Expectations

**Local Development**:

- Simple queries: <1 second
- Multi-turn conversations: 2-5 seconds per turn
- Complex multi-tool: <15 seconds
- Health checks: <500ms

**Render Deployment**:

- First request (cold start): 30+ seconds
- Simple queries: <5 seconds
- Multi-turn conversations: 5-10 seconds per turn
- Complex multi-tool: <45 seconds

## System Architecture Overview

### Microservices Architecture

- **Chat Service**: AI orchestration via OpenAI Agents SDK
- **Order Service**: Business analytics and order management
- **Product Service**: Semantic search with ChromaDB vectors

### Model Context Protocol (MCP) Integration

- **FastAPI-MCP** (*fastapi-mcp*):
  - Zero-config tool publication for Order and Product services
  - Each service automatically exposes its endpoints as MCP tools
  - No manual tool definitions needed - FastAPI endpoints become LLM-callable tools
  - Preserves OpenAPI schemas for accurate parameter validation

- **OpenAI-Agents-MCP** (*openai-agents-mcp*):
  - Create an agent with specific MCP servers you want to use
  - Discovers available tools from Order/Product services at runtime

- **Benefits of MCP Approach**:
  - Services remain standard FastAPI apps - no LLM-specific code needed
  - Tools stay in sync with API endpoints automatically
  - Type safety and validation preserved end-to-end
  - Easy to add new services - just mount FastAPI-MCP and they're discoverable

### RAG Implementation

- ChromaDB vector database with ~51k product embeddings
- Semantic search with natural language understanding
- Metadata filtering for precise results

### Enhanced Mock API

- Order service provides business intelligence beyond basic CRUD
- Profit analysis, customer demographics, category performance
- Production safety limits for large dataset handling
- Pagination support for browsing 51k+ orders

### Multi-Dataset Integration

- Single chat interface queries both products and orders
- Automatic tool selection based on user intent
- Context maintained across conversation turns
- Natural language pagination for large result sets

### Production Features

- Real-time SSE streaming for transparent AI operations
- Token optimization through field exclusion
- Graceful error handling and input validation
- Multi-turn conversation support with session management
- Simple performance benchmarks
