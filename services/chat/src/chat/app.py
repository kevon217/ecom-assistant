# services/chat/src/chat/app.py - Complete with graceful handling

import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from agents.exceptions import UserError
from agents_mcp import RunnerContext
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from libs.ecom_shared.context import AppContext
from libs.ecom_shared.logging import get_logger
from libs.ecom_shared.models import HealthResponse, HealthStatus

from .config import config
from .models import ChatRequest, ChatResponse
from .orchestrator import AgentOrchestrator
from .session import SessionManager, SessionStore, get_session

logger = get_logger(__name__)

router = APIRouter(tags=["chat"])

# --- Health Check Endpoint ------------------------------------------------------


@router.get("/health", response_model=HealthResponse)
async def health():
    """Basic health check endpoint without orchestrator dependency."""
    details = {
        "service": "chat",
        "status": "ok",
        "version": "0.8.0",
        "config": {
            "session_store": config.session_store_path,
            "order_mcp": config.order_mcp_url,
            "product_mcp": config.product_mcp_url,
            "model": config.agent_model,
        },
    }
    return HealthResponse(status=HealthStatus.OK, details=details, version="0.8.0")


# --- Debug Endpoint -------------------------------------------------------------


@router.get("/debug/connections")
async def debug_connections():
    """Test connectivity to MCP services - simpler version."""
    import httpx

    # Get orchestrator status if available
    orchestrator_status = {}
    try:
        orch = get_orchestrator()
        orchestrator_status = orch.get_health_status()
    except:
        orchestrator_status = {"error": "Orchestrator not available"}

    results = {
        "timestamp": time.time(),
        "orchestrator": orchestrator_status,
        "mcp_urls": {"order": config.order_mcp_url, "product": config.product_mcp_url},
        "connectivity": {"order_service": {}, "product_service": {}},
    }

    # Quick connectivity test with short timeout
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Test order service
        try:
            # Just check if SSE endpoint responds
            async with client.stream(
                "GET", config.order_mcp_url, headers={"Accept": "text/event-stream"}
            ) as response:
                results["connectivity"]["order_service"] = {
                    "reachable": True,
                    "status": response.status_code,
                    "is_sse": "text/event-stream"
                    in response.headers.get("content-type", ""),
                }
        except httpx.TimeoutException:
            results["connectivity"]["order_service"] = {
                "reachable": True,
                "status": "timeout",
                "note": "SSE endpoint exists but slow to connect",
            }
        except Exception as e:
            results["connectivity"]["order_service"] = {
                "reachable": False,
                "error": type(e).__name__,
                "message": str(e),
            }

        # Test product service
        try:
            async with client.stream(
                "GET", config.product_mcp_url, headers={"Accept": "text/event-stream"}
            ) as response:
                results["connectivity"]["product_service"] = {
                    "reachable": True,
                    "status": response.status_code,
                    "is_sse": "text/event-stream"
                    in response.headers.get("content-type", ""),
                }
        except httpx.TimeoutException:
            results["connectivity"]["product_service"] = {
                "reachable": True,
                "status": "timeout",
                "note": "SSE endpoint exists but slow to connect",
            }
        except Exception as e:
            results["connectivity"]["product_service"] = {
                "reachable": False,
                "error": type(e).__name__,
                "message": str(e),
            }

    # Add summary
    all_reachable = all(
        results["connectivity"][svc].get("reachable", False)
        for svc in ["order_service", "product_service"]
    )

    results["summary"] = {
        "all_services_reachable": all_reachable,
        "mcp_connected": orchestrator_status.get("mcp_connected", False),
        "tools_available": orchestrator_status.get("tool_count", 0) > 0,
    }

    return results


# --- Dependency Overrides -------------------------------------------------------


def get_orchestrator() -> AgentOrchestrator:
    orch = app.state.orchestrator
    if orch is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return orch


def get_runner_context(session=Depends(get_session)) -> RunnerContext:
    # Build AppContext from session metadata
    ctx = AppContext(
        user_id=session.get("metadata", {}).get("user_id"),
        correlation_id=session.get("metadata", {}).get("correlation_id"),
        session_id=session["id"],
        request_id=session["id"],
    )
    # Return RunnerContext for agents-mcp (ignores YAML config)
    return RunnerContext(**ctx.to_dict())


# --- Chat Endpoint with graceful fallback ---------------------------------------


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    context: RunnerContext = Depends(get_runner_context),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    """Handle chat requests gracefully, with or without MCP tools."""

    start_time = time.time()
    orchestrator.session_manager.add_message(context.session_id, "user", req.message)

    try:
        # Process message - will work with or without MCP
        reply = await orchestrator.process_message(req.message, context)

    except Exception as e:
        logger.error(f"Error during chat processing: {e}", exc_info=True)

        # Provide a helpful fallback response
        if "MCP" in str(e) or "tool" in str(e).lower():
            reply = (
                "I'm currently unable to access some specialized tools, but I can still help you "
                "with general questions about products and orders. What would you like to know?"
            )
        else:
            # For other errors, try a direct OpenAI call as ultimate fallback
            try:
                import openai

                client = openai.AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                response = await client.chat.completions.create(
                    model=config.agent_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful e-commerce assistant.",
                        },
                        {"role": "user", "content": req.message},
                    ],
                    temperature=0.7,
                    max_tokens=500,
                )
                reply = response.choices[0].message.content
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                reply = "I apologize, but I'm having technical difficulties. Please try again in a moment."

    orchestrator.session_manager.add_message(context.session_id, "assistant", reply)

    return ChatResponse(
        message=reply,
        session_id=context.session_id,
        correlation_id=context.correlation_id,
        duration_ms=(time.time() - start_time) * 1000,
    )


# --- Streaming Chat Endpoint ----------------------------------------------------


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    context: RunnerContext = Depends(get_runner_context),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    """
    Stream chat responses with real-time tool execution feedback via SSE.
    Checks MCP connection before starting the stream.
    """
    # Record the user's message
    orchestrator.session_manager.add_message(context.session_id, "user", req.message)

    # Ensure MCP is checked BEFORE creating the stream
    try:
        await orchestrator.ensure_mcp_connected()
    except Exception as e:
        logger.warning(f"MCP connection check failed: {e}")
        # Continue anyway - we'll work without tools

    # Now start the streaming run (this is sync)
    try:
        stream = orchestrator.process_message_streaming(req.message, context)
    except Exception as e:
        logger.error(f"Error starting streaming: {e}", exc_info=True)

        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'error': 'Unable to start chat stream'})}\n\n"

        return StreamingResponse(error_stream(), media_type="text/event-stream")

    async def event_generator():
        # Track state
        full_response = []
        active_tools = {}  # Track tool_id -> tool_name mapping
        last_heartbeat = time.time()

        try:
            async for evt in stream.stream_events():
                try:
                    # Send heartbeat every 20 seconds
                    if time.time() - last_heartbeat > 20:
                        yield ": heartbeat\n\n"
                        last_heartbeat = time.time()

                    # Handle based on event type
                    if evt.type == "raw_response_event":
                        if hasattr(evt.data, "choices") and evt.data.choices:
                            delta = evt.data.choices[0].delta

                            # Stream content chunks
                            if hasattr(delta, "content") and delta.content:
                                chunk = delta.content
                                full_response.append(chunk)
                                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"

                            # Detect tool calls
                            if hasattr(delta, "tool_calls") and delta.tool_calls:
                                for tc in delta.tool_calls:
                                    if hasattr(tc, "function") and hasattr(
                                        tc.function, "name"
                                    ):
                                        tool_name = tc.function.name
                                        tool_id = getattr(tc, "id", tool_name)

                                        if tool_id not in active_tools:
                                            active_tools[tool_id] = tool_name
                                            friendly_name = (
                                                orchestrator.get_tool_friendly_name(
                                                    tool_name
                                                )
                                            )
                                            yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name, 'message': f'🔧 {friendly_name}...'})}\n\n"

                    elif evt.type == "run_item_stream_event":
                        event_name = evt.name

                        if event_name == "tool_output":
                            if hasattr(evt.item, "tool_call_id"):
                                tool_id = evt.item.tool_call_id
                                if tool_id in active_tools:
                                    tool_name = active_tools.pop(tool_id, "unknown")
                                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': tool_name, 'message': '✓ Complete'})}\n\n"

                                    # Check for tool errors
                                    if hasattr(evt.item, "error") and evt.item.error:
                                        yield f"data: {json.dumps({'type': 'tool_error', 'tool': tool_name, 'error': str(evt.item.error)})}\n\n"

                        elif event_name == "mcp_list_tools":
                            yield f"data: {json.dumps({'type': 'info', 'message': 'Discovering available tools...'})}\n\n"

                    elif evt.type == "agent_updated_stream_event":
                        new_agent_name = getattr(evt.new_agent, "name", "Assistant")
                        yield f"data: {json.dumps({'type': 'agent_changed', 'agent': new_agent_name})}\n\n"

                    # Debug mode
                    elif config.debug:
                        yield f"data: {json.dumps({'type': 'debug', 'event_type': evt.type, 'data': str(evt)[:100]})}\n\n"

                except Exception as e:
                    logger.error(f"Error processing event: {e}", exc_info=True)
                    if config.debug:
                        yield f"data: {json.dumps({'type': 'debug_error', 'error': str(e)})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': 'Stream processing failed'})}\n\n"

        finally:
            # Save the complete response
            if full_response:
                complete_message = "".join(full_response)
                try:
                    orchestrator.session_manager.add_message(
                        context.session_id, "assistant", complete_message
                    )
                except Exception as e:
                    logger.error(f"Failed to save message: {e}")

            # Signal stream completion
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )


# --- Lifespan / Startup & Shutdown ----------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    startup_delay = config.startup_delay
    if startup_delay > 0:
        logger.info(
            f"Waiting {startup_delay} seconds for other services to initialize..."
        )
        await asyncio.sleep(startup_delay)

    # STARTUP
    # ensure session storage directory exists
    sessions_path = config.session_store_path or "/tmp/chat_sessions"
    os.makedirs(sessions_path, exist_ok=True)
    SessionStore.initialize(sessions_path)

    # instantiate session manager and orchestrator
    session_mgr = SessionManager(ttl_minutes=config.session_ttl_minutes)
    app.state.session_manager = session_mgr
    app.state.orchestrator = AgentOrchestrator(session_manager=session_mgr)

    # pre-load templates and try initial MCP connection (non-blocking)
    await app.state.orchestrator.load_templates()

    yield  # application is running

    # SHUTDOWN
    await app.state.orchestrator.cleanup()
    await SessionStore.flush()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="ECOM-ASSISTANT Chat Service",
        version="0.8.0",
        lifespan=lifespan,
    )

    # CORS policy
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()
