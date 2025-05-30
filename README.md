# E-Commerce Assistant

Demo project for microservices architecture implementing an AI-powered e-commerce assistant using OpenAI's Agents SDK, Model Context Protocol (MCP), FastAPI, and Pydantic V2.

## Overview

This system configures an E-Commerce AI assistant that can:

- **Leverage metadata** to understand data landscape
- **Search products** using semantic search and complex filters
- **Analyze orders** to provide business insights and customer intelligence
- **Stream responses** in real-time with tool execution transparency
- **Scale independently** with microservices architecture

The assistant leverages OpenAI's Agents SDK and MCP extensions to orchestrate multiple specialized services, providing a natural conversational interface for e-commerce operations.

## Architecture

**Note**: User Interface NOT yet implemented

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                           │
│                    (Web/Mobile/API Client)                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │ SSE
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Chat Service (:8001)                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  OpenAI Agents SDK                        │  │
│  │  • Automatic tool discovery via MCP                       │  │
│  │  • Tool selection and chaining                            │  │
│  │  • Streaming response synthesis                           │  │
│  └───────────────────────┬───────────────┬───────────────────┘  │
└──────────────────────────┼───────────────┼──────────────────────┘
                 MCP/SSE   │               │  MCP/SSE
                ┌──────────▼───────┐  ┌────▼──────────┐
                │ Order Service    │  │Product Service│
                │    (:8002)       │  │   (:8003)     │
                │                  │  │               │
                │ • Order analytics│  │ • Semantic    │
                │ • Customer stats │  │   search      │
                │ • Sales metrics  │  │ • Vector DB   │
                │                  │  │ • Filters     │
                └────────┬─────────┘  └──────┬────────┘
                         │                   │
                    ┌────▼────┐         ┌────▼────┐
                    │  CSV    │         │ChromaDB │
                    │  Data   │         │ Vectors │
                    └─────────┘         └─────────┘
```

### Key Technologies

- **OpenAI Agents SDK** - framework for building agentic AI apps
- **Model Context Protocol (MCP)** - standardized protocol to provide tools and context for agents
- **openai-agents-mcp** - MCP extension package for openai-agents
- **fastapi-mcp** - zero-config MCP tool publication for FastAPI services
- **ChromaDB** - vector database for semantic search
- **Pydantic v2** - tool schemas and data validation
- **Docker** - containerized microservices

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- OpenAI API Key

### Local Development

1. **Clone and setup**

   ```bash
   git clone https://github.com/kevon217/ecom-assistant.git
   cd ecom-assistant
   cp .env.sample .env
   # Add your OPENAI_API_KEY to .env, set service configs (also see service config.py for defaults)
   ```

2. **Build and start services**

   ```bash
   make build
   make up
   ```

3. **Verify health**

   ```bash
   curl http://localhost:8001/health  # Chat service
   curl http://localhost:8002/health  # Order service
   curl http://localhost:8003/health  # Product service
   ```

4. **Test the assistant**

   ```bash
   curl -X POST http://localhost:8001/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Show me wireless headphones under $100"}'
   ```

## Testing

### Postman Collection

[Postman Testing Guide](postman/Postman%20Testing%20Guide.md) — step-by-step walkthrough of how to import and run the collection.

- `ecom_assistant_postman_collection.json` - Full test suite with 100+ tests
- `ecom_assistant_local_env.json` - Environment for local testing
- `ecom_assistant_render_env.json` - Environment for production testing
- `Postman Testing Guide.md` - Detailed testing instructions

The collection includes:

- 10 challenge requirement scenarios
- Multi-turn conversation tests
- Edge case handling
- Performance benchmarks
- Multi-tool orchestration demos

### Run Postman Tests

1. Import collection and appropriate environment file into Postman
2. Update environment variables if needed (especially for Render URLs)
3. Run collection with 500ms delay between requests
4. Expected: 98%+ pass rate locally, 95%+ on Render

**Note**: Render's free plan (512 MB RAM, 0.1 CPU) leads to slow performance and memory overflow when handling multiple large ChromaDB queries. Time was not spent optimizing for free plan. Services may fail and need to restart. No issues when running on localhost in more forgiving environment. Run curl below to check mcp server and agent tool avability status.

```
curl -X GET https://ecom-chat-itzk.onrender.com/debug/connections
```

## 💬 Example Interactions

### Product Search

```
User: "I need good wireless headphones under $50 with high ratings"
Assistant: I'll help you find wireless headphones under $50 with good ratings. Let me search for those.

🔧 Searching for products...

Based on my search, here are the best wireless headphones under $50:

1. **JBL Tune 510BT** - $39.99
   - Rating: 4.3/5 (8,456 reviews)
   - Bluetooth 5.0, 40-hour battery
   - Foldable design, great for travel

2. **Anker Soundcore Life Q20** - $49.99
   - Rating: 4.4/5 (15,234 reviews)
   - Active noise cancellation
   - 40-hour battery life
```

### Order Analysis

```
User: "Show me profit analysis for customer 12345"
Assistant: I'll analyze the profit data for customer 12345.

🔧 Analyzing customer purchase history...

Customer #12345 Analysis:

- Total Orders: 47
- Total Revenue: $3,499.85
- Total Profit: $523.45 (15% margin)
- Average Order Value: $74.46
- Favorite Category: Technology (60% of orders)
- Member Since: January 2022
```

### Complex Multi-Tool Query

```
User: "Get my order 37077 and tell me about high profit products and profit by gender"
Assistant: I'll get your specific order details and analyze our profit data.

🔧 Getting order details...
🔧 Analyzing high profit products...
🔧 Calculating profit by gender demographics...

**Your Order #37077:**
- Customer: 12345
- Category: Electronics
- Sale Amount: $299.99
- Profit: $89.99 (30% margin)
- Priority: High

**High Profit Products Analysis:**
- 15 orders with profit ≥ $100
- Top performer: $245 profit margin
- Categories: Electronics (60%), Fashion (40%)

**Profit by Gender Demographics:**
- Male customers: $234,567 total profit (55%)
- Female customers: $198,432 total profit (45%)
- Average order value similar across segments
```

## 🛠️ Development

### Project Structure

```
ecom-assistant/
├── services/                         # Microservices architecture
│   ├── chat/                         # AI orchestration service (:8001)
│   │   ├── src/chat/
│   │   │   ├── app.py                # FastAPI endpoints, SSE streaming
│   │   │   ├── orchestrator.py       # OpenAI Agents SDK integration
│   │   │   ├── session.py            # Session management, UUID tracking
│   │   │   ├── models.py             # Chat request/response models
│   │   │   ├── config.py             # Service configuration
│   │   │   └── prompts/              # Jinja2 templates
│   │   ├── tests/                    # Unit & integration tests
│   │   │   ├── unit/                 # Service-specific tests
│   │   │   └── integration/          # MCP protocol, streaming tests
│   │   ├── Dockerfile                # Development container
│   │   ├── Dockerfile.render         # Production container
│   │   └── pytest.ini                # Test configuration
│   │
│   ├── order/                        # Order analytics service (:8002)
│   │   ├── src/order/
│   │   │   ├── app.py                # FastAPI + MCP tools
│   │   │   ├── data_service.py       # Business analytics, pandas operations
│   │   │   ├── models.py             # OrderItem, analytics models
│   │   │   └── config.py             # Service configuration
│   │   └── tests/                    # Comprehensive test coverage
│   │
│   └── product/                      # Product search service (:8003)
│       ├── src/product/
│       │   ├── app.py                # FastAPI + MCP tools
│       │   ├── services/data_service.py  # Search orchestration
│       │   ├── stores/chroma_store.py    # ChromaDB integration
│       │   ├── interfaces.py         # Storage abstractions
│       │   ├── models.py             # ProductItem, search models
│       │   └── config.py             # Service configuration
│       └── tests/                    # Unit, integration, mock tests
│
├── libs/ecom_shared/                 # Shared libraries
│   ├── config.py                     # Common configuration patterns
│   ├── context.py                    # Request context management
│   ├── health.py                     # Standardized health checks
│   ├── logging.py                    # Structured logging setup
│   ├── middleware.py                 # Common FastAPI middleware
│   └── models.py                     # Shared data models
│
├── cleaner/                          # Data processing pipeline
│   ├── data_cleaner.py               # Schema-driven field processing
│   ├── pipeline.py                   # Orchestration & validation
│   ├── config.yaml                   # Processing rules & field types
│   ├── tests/test_cleaning.py        # Pipeline validation tests
│   └── utils.py                      # Text normalization utilities
│
├── data/                             # Data storage & processing
│   ├── orders_cleaned.csv            # 51k+ orders dataset
│   ├── products_cleaned.csv          # ~5k products dataset
│   ├── processed/                    # Cleaned datasets
│   │   ├── latest/                   # Symlinks to current data
│   │   ├── runs/20250526_*/          # Timestamped processing runs
│   │   └── analysis/profiles/        # Data quality reports (HTML)
│   ├── chroma/                       # ChromaDB persistence
│   └── sessions/                     # Chat session storage
│
├── scripts/                          # Automation & utilities
│   ├── bootstrap/                    # Data initialization
│   │   ├── load_vectors.py           # ChromaDB bootstrap pipeline
│   │   └── bootstrap.sh              # Environment setup
│   └── dev/                          # Development utilities
│
├── postman/                          # API testing
│   ├── ecom_assistant_postman_collection.json
│   ├── ecom_assistant_local_env.json
│   ├── ecom_assistant_render_env.json
│   └── Postman Testing Guide.md
│
├── .github/workflows/ci.yml          # GitHub Actions CI/CD
├── docker compose.yaml               # Local development environment
├── render.yaml                       # Production deployment config
├── Makefile                          # Development commands
├── pyproject.toml                    # Python dependencies (uv)
└── uv.lock                           # Dependency lock file
```

### Service Details

#### Chat Service (Port 8001)

- Session management with UUID tracking and TTL
- OpenAI Agents SDK with openai-agents-mcp for tool orchestration
- Server-Sent Events streaming with real-time tool feedback
- Jinja2 prompt templates with context injection

#### Order Service (Port 8002)

- 51k+ historical orders dataset
- Business intelligence: profit analysis, customer stats, demographics
- Safety features: raw data record limits, field exclusion for LLM
- FastAPI with fastapi-mcp for zero-config MCP tool exposure

#### Product Service (Port 8003)

- 5k+ products with ChromaDB vector embeddings
- Semantic search with natural language understanding
- Advanced filtering: price, rating, category, metadata
- FastAPI with fastapi-mcp for automatic tool publication

**Note**: Current implementation rebuilds ChromaDB from scratch on each deployment... Future iterations would implement incremental updates using embed_checksums and enable caching for more efficient vector database management and deployment.

## Key Features

### Model Context Protocol (MCP) Integration

- **FastAPI-MCP**: Order and Product services use fastapi-mcp to automatically expose endpoints as MCP tools
- **Zero Configuration**: Services remain standard FastAPI apps with MCP capabilities added via simple app mounts
- **OpenAI-Agents-MCP**: Extends OpenAI Agents SDK to support MCP. Chat service leverages Agent and RunnerContext to incorporate MCP servers and additional AppContext (mcp_agent.config.yaml not needed as FastAPI-MCP covers tool schemas)
- **Agent Orchestration**: Custom orchestrator class helps facilitate dynamic tool discovery,prompt management, and further customizations

### Real-time Streaming

Server-Sent Events provide transparent tool execution:

```javascript
{"type": "tool_start", "tool": "semantic_search", "message": "🔧 Searching for products..."}
{"type": "content", "content": "I found 5 products matching your criteria..."}
{"type": "tool_end", "tool": "semantic_search", "message": "✓ Complete"}
{"type": "done"}
```

### Production Safety

- Dataset limits to prevent LLM token overflow
- Sensitive field exclusion (order_id hidden from LLM)
- Token optimization through Pydantic field configuration
- Graceful error handling and input validation

## Deployment

**Note:**
The `OPENAI_API_KEY` is **only required** by the **Chat service**.
The Order and Product services do not call OpenAI and therefore do not need this secret.

### Environment Variables

```bash
# Chat
CHAT_SERVICE_URL=http://localhost:8001
CHAT_STARTUP_DELAY=5
CHAT_SESSION_STORE_PATH=services/chat/data/sessions
CHAT_SESSION_TTL=60

# Agent
OPENAI_API_KEY=sk...
CHAT_SYSTEM_PROMPT_TEMPLATE=system_prompt.j2
CHAT_INCLUDE_STRATEGIES=False
AGENT_MODEL=gpt-4o-mini

# Order
ORDER_MCP_URL=http://localhost:8002/mcp
ORDER_DATA_PATH=data/orders_cleaned.csv

# Product
PRODUCT_MCP_URL=http://localhost:8003/mcp
PRODUCT_DATA_PATH=data/products_cleaned.csv
EMBED_MODEL=all-MiniLM-L6-v2
CHROMA_PERSIST_DIR=data/chroma
```

### Render Deployment

1. Fork repository
2. Connect to Render
3. Deploy using `render.yaml` blueprint
4. Update service URLs in chat service environment
5. Add `OPENAI_API_KEY` in Render dashboard

### Performance

- Simple queries: <2s response time
- Complex multi-tool queries: <15s
- Streaming latency: <100ms per chunk
- Vector search: Sub-second for ~5k products
- Cold start on Render: 30-60s first request
