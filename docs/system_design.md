# E-Commerce Assistant Architecture

## Overview

A modular, microservice-driven e-commerce assistant that provides contextual, RAG-powered answers about products and orders. Designed around the Model Context Protocol (MCP) for LLM integration, robust data pipelines, and clear service boundaries.

---

## Guiding Principles

- **Modular Microservices**
  - Each service handles a single responsibility and publishes its capability set as MCP tools.

- **Separation of Concerns**
  - Data cleaning, embedding, and serving are distinct stages linked by shared contracts.

- **Standardized Interfaces**
  - REST + OpenAPI for external UIs and integrations
  - FastAPI-MCP for zero-config LLM tool publication:
     1. Native FastAPI integration preserving schemas and docs
     2. Server-Sent Events (SSE) transport for real-time communication
     3. Authentication using existing FastAPI dependencies

- **LLM Orchestration**
  - Chat service uses OpenAI Agents SDK with MCP tool integration for dynamic tool discovery and invocation in LLM workflows.

- **Vector Storage Bootstrap**
  - StorageManager handles delta synchronization via embed_checksums, enabling incremental updates to ChromaDB collections.

- **Shared-Data Disk Strategy**
  - One shared `/data` volume holds both processed CSVs (`/data/processed`) and the ChromaDB store (`/data/chroma`) across environments.

- **Graceful Degradation & Observability**
  - Standardized `/health` endpoints, structured logs, retries/fallbacks, and full test coverage.

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend Framework** | FastAPI | RESTful APIs, automatic OpenAPI docs, async support |
| **AI/Chat** | OpenAI Agents SDK | LLM orchestration, tool calling, conversation management |
| **Vector Search** | ChromaDB | Semantic search, embeddings storage, metadata filtering |
| **Data Processing** | Pandas + Pydantic | Data cleaning, validation, transformation |
| **Tool Integration** | FastAPI-MCP | Zero-config MCP server integration with FastAPI apps |
| **Inter-Service Communication** | MCP Protocol | Standardized tool discovery and invocation for AI agents |
| **Development** | uv, pre-commit, pytest | Package management, code quality, testing |
| **Deployment** | Docker + Render.com | Containerization, cloud hosting, CI/CD |
| **UI** | Gradio | Web-based chat interface for testing and demos |

---

## System Design

**1. Data Pipeline**

- **Raw Data**: `orders.csv` + `products.csv`
- **Data Cleaner**: Schema-driven processing → cleaned CSVs with `embed_text` and `embed_checksums`
- **Vector Bootstrap**: StorageManager performs delta sync, embeds new/changed records → ChromaDB
- **Storage**: Shared `/data` volume with processed CSVs and ChromaDB collections

**2. Microservices Architecture**

| Service | Port | Purpose | Key Components |
|---------|------|---------|----------------|
| **Product Service** | :8003 | Semantic search | ProductDataService, ChromaProductStore (4,882 products), ProductItemLLM optimization |
| **Order Service** | :8002 | Business analytics | OrderDataService, comprehensive analytics (profit, customer stats, demographics), safety limits |
| **Chat Service** | :8001 | LLM orchestration | AgentOrchestrator, OpenAI Agents SDK, SSE streaming, session management |
| **Web UI** | :8000 | User interface | Gradio chat interface, session management |

**3. Communication Flow**

1. **User** → Web UI → Chat Service
2. **Chat Service** → OpenAI Agents SDK → determines tools needed
3. **Agent** → MCP protocol → Product/Order services
4. **Services** → ChromaDB/CSV data → return results
5. **Agent** → synthesizes response → streams back to user

## Repository Structure

```
ecom-assistant/
├── services/
│   ├── order/       # FastAPI + MCP tools, OrderDataService, pandas analytics
│   ├── product/     # FastAPI + MCP tools, ProductDataService + ChromaProductStore
│   └── chat/        # FastAPI + OpenAI Agents SDK, AgentOrchestrator, SSE streaming
├── libs/ecom_shared/ # Shared config, context, health, logging, models, prompts
├── cleaner/         # Enhanced data pipeline with DataCleaner + ModelValidator
├── data/
│   ├── processed/   # Cleaned CSVs with embed_text fields
│   ├── chroma/      # ChromaDB persistence
│   └── sessions/    # Chat session storage
├── infra/
│   ├── docker-compose.yml
│   └── render.yaml    # Shared-data disk, bootstrap job, service definitions
├── dev-tools/        # Smoke tests & debugging scripts
├── scripts/
│   └── bootstrap/   # Vector initialization & data setup scripts
├── Makefile          # sync, lint, format, test, up/down
├── pyproject.toml    # Standardized deps via uv
├── uv.lock
└── README.md
```

---

## Decisions Made

- **Package Management:** Unified on `uv` for reproducible installs—no Poetry.
- **AI Integration:** OpenAI Agents SDK for LLM orchestration with FastAPI-MCP for zero-config tool publication.
- **Storage Architecture:** Interface-based design with ChromaProductStore implementation for easy testing/swapping.
- **Data Strategy:** ChromaDB as single source of truth for products; delta sync via embed_checksums.
- **Bootstrap Process:** StorageManager handles incremental vector updates and data synchronization.

## Recent Enhancements & Production Features

- **Enhanced Order Analytics:** Comprehensive business intelligence endpoints including profit analysis, customer demographics, category sales, and shipping cost analytics.
- **LLM Safety Measures:** Field exclusion patterns (order_id hidden from LLM), 1000-record safety limits for massive datasets, and token optimization.
- **Advanced Search Capabilities:** Complex filtering with profit thresholds, priority levels, category filters, and multi-criteria search operations.
- **Production-Ready Testing:** Comprehensive test suites with unit, integration, and business workflow testing via enhanced Postman collection.
- **Route Optimization:** Resolved path collision issues by strategic endpoint ordering (specific routes before parameterized routes).
- **Pydantic v2 Migration:** Updated field validation patterns (regex → pattern), enhanced model validation and LLM optimization.

---

## Service Boundaries & Data Flow

- **Data Cleaner**
  - Data pipeline with schema-driven field processing, Pydantic validation, and embed_text generation → `data/processed/latest/*.csv`.

- **Vector Bootstrap**
  - StorageManager reads cleaned data with embed_checksums.
  - Performs delta sync: identifies new/changed records via checksum comparison.
  - Batch embeds and upserts only changed data to `/data/chroma`.

- **Order Service**
  - OrderDataService with comprehensive business analytics (51k+ orders dataset).
  - Enhanced endpoints: customer stats, profit analysis, gender demographics, category sales.
  - Safety measures: 1000-record limits to protect LLM, LLM field exclusion (order_id hidden).
  - Advanced filtering: profit thresholds, priority levels, complex search with multiple criteria.
  - FastAPI endpoints + MCP tools for complete business intelligence.

- **Product Service**
  - ProductDataService with ChromaProductStore (4,882 products with vector embeddings).
  - ProductItemLLM model with 80% token optimization for LLM efficiency.
  - Semantic search with complex document filters and metadata discovery.
  - FastAPI endpoints + MCP tools for intelligent product search and recommendations.

- **Chat Service**
  - `/chat` & `/chat/stream` → `AgentOrchestrator`:
    1. Renders Jinja2 system prompt templates.
    2. Uses OpenAI Agents SDK for tool discovery and calling.
    3. Streams responses via SSE for real-time user experience.

---

## Proposed Lean-Down Roadmap & Milestones

1. **v0.0** – Exploratory Data Analysis
2. **v0.1** – System Design & Stack
3. **v0.2** – Data Cleaning & Prep
4. **v0.3** – Project Setup & CI Skeleton
5. **v0.4** – Order Service + MCP tests
6. **v0.5** – Product Service + MCP tests
7. **v0.6** – Chat Service Core & Orchestrator
8. **v0.7** – Agents SDK + MCP integration
9. **v0.8** – Parallel Processing & Performance
10. **v0.9** – Guardrails, Observability, Structured Logging
11. **v1.0** – Optional UI & Frontend Integration
12. **v1.1** – Full CI/CD & Render Deployment
13. **v1.2** – Documentation & Onboarding
14. **v1.3** – Postman Collection & CODEOWNERS
