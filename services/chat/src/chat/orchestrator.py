# services/chat/src/chat/orchestrator.py - Using MCPServerSse for FastAPI-MCP services

import asyncio
import logging
import os
from typing import Any, Dict, List

from agents import RunConfig, Runner
from agents.mcp import MCPServerSse  # Changed from MCPServerStreamableHttp
from agents_mcp import Agent, RunnerContext
from jinja2 import Environment, FileSystemLoader, select_autoescape
from libs.ecom_shared.context import AppContext

from .config import config

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrator that uses MCPServerSse to connect to FastAPI-MCP services.
    """

    def __init__(self, session_manager):
        self.session_manager = session_manager

        # Load prompt templates
        prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
        self.env = Environment(
            loader=FileSystemLoader(prompts_dir),
            autoescape=select_autoescape(),
        )
        try:
            tpl_file = config.system_prompt_template.split("/")[-1]
            self.system_tpl = self.env.get_template(tpl_file)
            logger.info(f"Loaded system prompt template: {tpl_file}")
        except Exception as e:
            logger.warning(f"Could not load system prompt template: {e}")
            self.system_tpl = None

        # Initialize MCP servers for our FastAPI services
        self.mcp_servers = []
        self._setup_mcp_servers()

        # Create agent with MCP servers
        self.agent = Agent(
            name="EcomAssistant",
            instructions="You are an E-commerce Assistant. Help users find products and check orders.",
            mcp_servers=self.mcp_servers,  # Pass the MCP server objects
        )

    def _setup_mcp_servers(self):
        """Set up MCPServerSse instances for our services."""
        # Get URLs from environment
        order_url = config.order_mcp_url
        product_url = config.product_mcp_url

        # Create MCP server instances using SSE
        self.order_server = MCPServerSse(
            params={
                "url": order_url,
                "timeout": config.tool_timeouts,
            },
            cache_tools_list=True,  # Cache for performance
        )

        self.product_server = MCPServerSse(
            params={
                "url": product_url,
                "timeout": config.tool_timeouts,
            },
            cache_tools_list=True,
        )

        self.mcp_servers = [self.order_server, self.product_server]
        logger.info(
            f"Configured MCP servers (SSE): order={order_url}, product={product_url}"
        )

    async def load_templates(self):
        """Load and validate templates during startup."""
        if self.system_tpl is None:
            logger.warning("System prompt template not available - using fallback")
        else:
            logger.info("Templates loaded successfully")

        # Start MCP server connections
        for server in self.mcp_servers:
            for attempt in range(5):
                try:
                    await server.connect()
                    break
                except Exception:
                    await asyncio.sleep(5)
            else:
                logger.error(
                    f"Could not connect to {server.params['url']} after retries"
                )

    async def cleanup(self):
        """Cleanup MCP server connections."""
        for server in self.mcp_servers:
            try:
                await server.cleanup()  # SSE uses cleanup() instead of __aexit__
            except Exception as e:
                logger.warning(f"Error closing MCP server: {e}")

    def _render_prompt(self, user_message: str, ctx: AppContext) -> str:
        if not self.system_tpl:
            return f"You are an E-com Assistant. User: {user_message}"
        history = self.session_manager.get_history(ctx.session_id)
        return self.system_tpl.render(
            user_message=user_message,
            history=history,
            include_strategies=config.include_strategies,
        )

    async def process_message(self, user_message: str, context: RunnerContext) -> str:
        """Process message asynchronously (fixed event loop issue)."""
        ctx_obj = AppContext(
            **{
                k: getattr(context, k, None)
                for k in ["user_id", "session_id", "correlation_id", "request_id"]
            }
        )
        prompt = self._render_prompt(user_message, ctx_obj)
        self.agent.instructions = prompt

        # Run with MCP servers already configured
        run_cfg = RunConfig(model=config.agent_model)
        result = await Runner.run(
            starting_agent=self.agent,
            input=user_message,
            context=context,
            run_config=run_cfg,
        )
        return result.final_output

    def process_message_streaming(self, user_message: str, context: RunnerContext):
        """Process message with streaming."""
        ctx_obj = AppContext(
            **{
                k: getattr(context, k, None)
                for k in ["user_id", "session_id", "correlation_id", "request_id"]
            }
        )
        prompt = self._render_prompt(user_message, ctx_obj)
        self.agent.instructions = prompt

        run_cfg = RunConfig(model=config.agent_model)
        return Runner.run_streamed(
            starting_agent=self.agent,
            input=user_message,
            context=context,
            run_config=run_cfg,
        )

    def get_health_status(self) -> Dict[str, Any]:
        """Return health status for FastAPI health endpoint."""
        # Get tool count from agent (tools are loaded by SDK)
        tool_count = 0
        if hasattr(self.agent, "_tools_cache"):
            # If tools are cached
            tool_count = len(self.agent._tools_cache)

        return {
            "agent_ready": True,
            "agent_name": self.agent.name,
            "model": config.agent_model,
            "template_loaded": self.system_tpl is not None,
            "tool_count": tool_count,
            "mcp_servers": [
                "order-service",
                "product-service",
            ],  # SSE servers don't have name attribute
        }

    def get_tool_friendly_name(self, tool_name: str) -> str:
        """Convert tool names to user-friendly messages."""
        tool_messages = {
            "get_orders_by_customer": "Searching your order history",
            "semantic_search": "Searching for products",
            "get_order_details": "Fetching order details",
            "search_products_by_category": "Browsing product categories",
            "get_customer_stats": "Analyzing your purchase history",
            "get_recent_orders": "Finding your recent orders",
        }
        return tool_messages.get(tool_name, f"Using {tool_name}")
