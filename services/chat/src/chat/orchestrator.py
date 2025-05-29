# services/chat/src/chat/orchestrator.py - Complete graceful MCP handling

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict

from agents import RunConfig, Runner
from agents.mcp import MCPServerSse
from agents_mcp import Agent, RunnerContext
from jinja2 import Environment, FileSystemLoader, select_autoescape
from libs.ecom_shared.context import AppContext

from .config import config

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrator with graceful MCP handling and dynamic tool discovery.
    Works with or without MCP servers being available.
    """

    def __init__(self, session_manager):
        self.session_manager = session_manager
        self._mcp_connected = False
        self._connection_lock = asyncio.Lock()
        self._last_connection_attempt = None
        self._connection_retry_interval = 30  # TODO: make this configurable

        # Store server configurations but don't create instances yet
        self._server_configs = []
        if config.order_mcp_url:
            self._server_configs.append(
                {"name": "order", "url": config.order_mcp_url, "instance": None}
            )
        if config.product_mcp_url:
            self._server_configs.append(
                {"name": "product", "url": config.product_mcp_url, "instance": None}
            )

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

        # Create agent with no MCP servers initially
        self.agent = Agent(
            name="EcomAssistant",
            instructions="You are an E-commerce Assistant. Help users find products and check orders.",
            mcp_servers=[],
        )  # TODO: make default instructions agnostic

        logger.info(
            "Orchestrator initialized. MCP servers will be connected dynamically."
        )

    async def _try_connect_mcp_servers(self) -> bool:
        """
        Attempt to connect to MCP servers. Returns True if any connected.
        This is called periodically to handle dynamic availability.
        """
        connected_servers = []
        any_connected = False

        for server_config in self._server_configs:
            try:
                # Create instance if needed
                if server_config["instance"] is None:
                    config["instance"] = MCPServerSse(
                        params={
                            "url": config["url"],
                            "timeout": 10,  # Shorter timeout for dynamic checking #TODO: make this configurable
                        },
                        cache_tools_list=True,
                    )

                # Try to connect if not already connected
                server = config["instance"]
                if not hasattr(server, "_connected") or not server._connected:
                    await server.connect()
                    logger.info(
                        f"✓ MCP server connected: {config['name']} at {config['url']}"
                    )

                connected_servers.append(server)
                any_connected = True

            except Exception as e:
                logger.debug(f"MCP server {config['name']} not available: {e}")
                # Don't remove the instance - we'll retry later

        # Update agent with currently connected servers
        self.agent.mcp_servers = connected_servers
        self._mcp_connected = len(connected_servers) > 0

        return any_connected

    async def _ensure_mcp_checked(self):
        """
        Check MCP server availability if enough time has passed since last attempt.
        This enables dynamic discovery without blocking requests.
        """
        async with self._connection_lock:
            now = datetime.now()

            # Check if we should attempt connection
            should_check = (
                self._last_connection_attempt is None
                or (now - self._last_connection_attempt).total_seconds()
                > self._connection_retry_interval
            )

            if should_check:
                self._last_connection_attempt = now
                try:
                    await self._try_connect_mcp_servers()
                    if self._mcp_connected:
                        logger.info(
                            f"MCP servers available: {len(self.agent.mcp_servers)} connected"
                        )
                    else:
                        logger.debug("No MCP servers currently available")
                except Exception as e:
                    logger.warning(f"Error checking MCP servers: {e}")

    async def ensure_mcp_connected(self):
        """Public method to ensure MCP is checked - called from endpoints."""
        await self._ensure_mcp_checked()

    async def load_templates(self):
        """Load templates and optionally try initial MCP connection."""
        if self.system_tpl is None:
            logger.warning("System prompt template not available - using fallback")
        else:
            logger.info("Templates loaded successfully")

        # Try initial connection but don't fail if it doesn't work
        try:
            await self._try_connect_mcp_servers()
        except Exception as e:
            logger.info(f"Initial MCP connection skipped: {e}")

    async def cleanup(self):
        """Cleanup MCP server connections."""
        for server_config in self._server_configs:
            if server_config["instance"] is not None:
                try:
                    await server_config["instance"].cleanup()
                except Exception as e:
                    logger.warning(f"Error closing MCP server {config['name']}: {e}")

    def _render_prompt(self, user_message: str, ctx: AppContext) -> str:
        """Render the prompt template."""
        if not self.system_tpl:
            # Fallback prompt that mentions tool availability
            base_prompt = "You are an E-commerce Assistant that helps users find products and check orders."  # TODO: make this configurable
            if not self._mcp_connected:
                base_prompt += " Note: External tools are temporarily unavailable, but you can still help with general questions."  # TODO: make this configurable
            return f"{base_prompt}\n\nUser: {user_message}"

        history = self.session_manager.get_history(ctx.session_id)
        return self.system_tpl.render(
            user_message=user_message,
            history=history,
            include_strategies=config.include_strategies,
            tools_available=self._mcp_connected,
        )

    async def process_message(self, user_message: str, context: RunnerContext) -> str:
        """Process message with graceful MCP handling."""
        # Check MCP availability (non-blocking)
        await self._ensure_mcp_checked()

        ctx_obj = AppContext(
            **{
                k: getattr(context, k, None)
                for k in ["user_id", "session_id", "correlation_id", "request_id"]
            }
        )
        prompt = self._render_prompt(user_message, ctx_obj)
        self.agent.instructions = prompt

        try:
            # Run with whatever MCP servers are currently available
            run_cfg = RunConfig(model=config.agent_model)
            result = await Runner.run(
                starting_agent=self.agent,
                input=user_message,
                context=context,
                run_config=run_cfg,
            )
            return result.final_output

        except Exception as e:
            logger.error(f"Error in message processing: {e}", exc_info=True)
            # Fallback response
            if "tool" in str(e).lower():
                return "I'm having trouble accessing some tools right now, but I can still help you with general questions about products and orders. What would you like to know?"  # TODO: make this configurable
            raise

    def process_message_streaming(self, user_message: str, context: RunnerContext):
        """
        Process message with streaming.
        Note: This must be sync because Runner.run_streamed returns a sync generator.
        MCP connection check happens in the endpoint before calling this.
        """
        ctx_obj = AppContext(
            **{
                k: getattr(context, k, None)
                for k in ["user_id", "session_id", "correlation_id", "request_id"]
            }
        )
        prompt = self._render_prompt(user_message, ctx_obj)
        self.agent.instructions = prompt

        try:
            run_cfg = RunConfig(model=config.agent_model)
            # This returns a synchronous generator
            return Runner.run_streamed(
                starting_agent=self.agent,
                input=user_message,
                context=context,
                run_config=run_cfg,
            )
        except Exception as e:
            logger.error(f"Error starting stream: {e}", exc_info=True)
            raise

    def get_health_status(self) -> Dict[str, Any]:
        """Return health status including MCP availability."""
        tool_count = len(self.agent.mcp_servers) if self._mcp_connected else 0

        # Get individual server status
        server_status = {}
        for server_config in self._server_configs:
            is_connected = False
            if server_config["instance"] is not None:
                # Check if the server has an active session
                is_connected = (
                    hasattr(server_config["instance"], "session")
                    and server_config["instance"].session is not None
                )

            server_status[server_config["name"]] = (
                "connected" if is_connected else "disconnected"
            )

        return {
            "agent_ready": True,
            "agent_name": self.agent.name,
            "model": config.agent_model,
            "template_loaded": self.system_tpl is not None,
            "mcp_servers": server_status,
            "mcp_connected": self._mcp_connected,
            "tool_count": tool_count,
            "last_mcp_check": self._last_connection_attempt.isoformat()
            if self._last_connection_attempt
            else None,
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
