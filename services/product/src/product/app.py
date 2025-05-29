# product-service/app.py

import os
import traceback
from typing import Any, Callable, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi_mcp import FastApiMCP
from libs.ecom_shared.logging import get_logger

from .config import config
from .models import (
    MetadataOptionsResponse,
    ProductItem,
    ProductItemLLM,
    SemanticSearchRequest,
)
from .services.data_service import ProductDataService
from .stores.chroma_store import ChromaProductStore

logger = get_logger(__name__)

app = FastAPI(
    title="Product Service",
    description="Manage product catalog and provide semantic and fuzzy keyword search",
)

# Add CORS middleware for Render deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.onrender.com", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_sse_headers_middleware(request: Request, call_next: Callable) -> Response:
    """Add required headers for SSE to work through Render's proxy"""
    response = await call_next(request)

    # Only touch GET /mcp that is actually streaming event-stream
    if (
        request.url.path == "/mcp"
        and request.method == "GET"
        and isinstance(response, StreamingResponse)
        and "event-stream" in response.headers.get("content-type", "")
    ):
        response.headers["X-Accel-Buffering"] = "no"
        response.headers["Cache-Control"] = "no-cache, no-transform"
        response.headers["Connection"] = "keep-alive"
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.on_event("startup")
def startup_event():
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        chroma_dir = config.chroma_persist_dir
        embedding_model = config.embedding_model

        # Create ChromaDB store
        chroma_store = ChromaProductStore(
            chroma_persist_dir=chroma_dir,
            embedding_model=embedding_model,
        )

        # Check if it needs initialization
        if chroma_store.count() == 0:
            logger.warning("ChromaDB is empty! Run bootstrap script first.")
            # Optionally, you could trigger bootstrap here
            # For now, just log the warning
        else:
            logger.info(f"ChromaDB initialized with {chroma_store.count()} products")

        # Inject store into service
        app.state.product_service = ProductDataService(store=chroma_store)


def get_product_service() -> ProductDataService:
    if not hasattr(app.state, "product_service"):
        # Fallback initialization
        chroma_dir = config.chroma_persist_dir
        embedding_model = config.embedding_model

        # Create ChromaDB store
        chroma_store = ChromaProductStore(
            chroma_persist_dir=chroma_dir,
            embedding_model=embedding_model,
        )

        # Inject store into service using interface pattern
        app.state.product_service = ProductDataService(store=chroma_store)
    return app.state.product_service


@app.get(
    "/health",
    response_model=Dict[str, str],
    tags=["products"],
    operation_id="product_health",
)
async def health():
    try:
        svc = get_product_service()
        store_ready = svc.store.health_check() if svc.store is not None else False
        return {
            "status": "ok",
            "store": "ready" if store_ready else "unavailable",
            "total_products": str(svc.store.count()) if store_ready else "0",
        }
    except Exception as e:
        logger.error("Health check failed", exc_info=e)
        return {"status": "error", "error": str(e), "store": "unavailable"}


@app.get(
    "/metadata/options",
    response_model=MetadataOptionsResponse,
    operation_id="get_metadata_options",
    tags=["products"],
)
async def get_metadata_options(
    field_name: str = Query(..., description="Name of metadata field"),
    limit: Optional[int] = Query(None, ge=1, description="Max values to return"),
    sort_by_count: bool = Query(True, description="Sort descending by count"),
):
    svc = get_product_service()
    try:
        options = svc.get_metadata_options(
            field_name, limit=limit, sort_by_count=sort_by_count
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Field '{field_name}' not found")
    return MetadataOptionsResponse(options=options)


@app.post(
    "/search/semantic",
    response_model=List[ProductItemLLM],
    operation_id="semantic_search",
    tags=["products"],
)
async def semantic_search(
    request: SemanticSearchRequest,
    service: ProductDataService = Depends(get_product_service),
):
    """
    Perform a semantic search with optional metadata and document filters,
    plus pagination (offset) and post-retrieval sorting.
    """
    return service.semantic_search(
        query=request.query,
        limit=request.limit,
        # offset=request.offset, #TODO: figure out pagination capabilities in later versions
        filters=request.filters,
        document_filters=request.document_filters,
        sort_by=request.sort_by,
        sort_order=request.sort_order,
    )


# Mount MCP with correct tags and operations
mcp = FastApiMCP(
    app,
    name="product-service",
    description="Product catalog and search service",
    describe_full_response_schema=True,
    include_tags=["products"],
    include_operations=[
        "get_metadata_options",
        "semantic_search",
        # "lexical_search",
        "product_health",
    ],
)
mcp.mount()
