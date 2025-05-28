# services/chat/tests/integration/conftest.py
# Integration test fixtures - use real components with FakeModel

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from fake_model import FakeModel

# Import FastAPI dependencies
from fastapi.middleware.cors import CORSMiddleware
from helpers import assert_response_format


@pytest.fixture
def fake_model():
    """Create FakeModel for integration testing."""
    return FakeModel()


@pytest.fixture
def mock_mcp_server_responses():
    """Mock responses for MCP servers."""
    return {
        "order-service": {
            "tools": [
                {
                    "name": "get_orders_by_customer",
                    "description": "Get orders for a specific customer",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"customer_id": {"type": "string"}},
                        "required": ["customer_id"],
                    },
                },
                {
                    "name": "get_order_details",
                    "description": "Get details for a specific order",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"order_id": {"type": "integer"}},
                        "required": ["order_id"],
                    },
                },
            ]
        },
        "product-service": {
            "tools": [
                {
                    "name": "semantic_search",
                    "description": "Search products using semantic similarity",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "limit": {"type": "integer", "default": 5},
                        },
                        "required": ["query"],
                    },
                },
                {
                    "name": "search_by_category",
                    "description": "Search products by category",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"category": {"type": "string"}},
                        "required": ["category"],
                    },
                },
            ]
        },
    }


@pytest.fixture
def integration_test_client(fake_model, mock_mcp_server_responses):
    """TestClient with real components but FakeModel for integration testing."""
    # Import after path setup
    # Create a test app without using lifespan to have more control
    from fastapi import FastAPI

    from chat.app import create_app, get_orchestrator, get_session, router
    from chat.orchestrator import AgentOrchestrator

    # Create app manually
    test_app = FastAPI(title="E-Commerce Chat Service (Test)")
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    test_app.include_router(router)

    # Manually initialize what lifespan would do
    with patch("chat.app.SessionStore") as mock_session_store:
        mock_session_store.initialize = MagicMock()
        mock_session_store.flush = AsyncMock()

        # Create session manager
        from chat.session import SessionManager

        session_manager = SessionManager(ttl_minutes=30)

        # Make session_manager a mock to track calls
        real_add_message = session_manager.add_message
        session_manager.add_message = MagicMock(side_effect=real_add_message)

        # Mock MCPServerSse
        with patch("chat.orchestrator.MCPServerSse") as mock_mcp_class:
            # Create mock MCP servers
            mock_order_server = MagicMock()
            mock_order_server.connect = AsyncMock(return_value=None)
            mock_order_server.cleanup = AsyncMock(return_value=None)
            mock_order_server.list_tools = AsyncMock(return_value=[])

            mock_product_server = MagicMock()
            mock_product_server.connect = AsyncMock(return_value=None)
            mock_product_server.cleanup = AsyncMock(return_value=None)
            mock_product_server.list_tools = AsyncMock(return_value=[])

            # Configure the mock class to return our servers
            mock_mcp_class.side_effect = [mock_order_server, mock_product_server]

            # Mock Agent to integrate with MCP
            with patch("chat.orchestrator.Agent") as mock_agent_class:
                # Create a mock agent that can handle MCP servers
                mock_agent = MagicMock()
                mock_agent.name = "EcomAssistant"
                mock_agent.instructions = "You are an E-commerce Assistant. Help users find products and check orders."

                # Create mock tools based on MCP responses
                mock_tools = []
                for service_name, service_data in mock_mcp_server_responses.items():
                    for tool_def in service_data["tools"]:
                        tool = MagicMock()
                        tool.name = tool_def["name"]
                        tool.description = tool_def["description"]
                        tool.inputSchema = tool_def["inputSchema"]
                        mock_tools.append(tool)

                mock_agent._tools_cache = mock_tools  # For health check
                mock_agent_class.return_value = mock_agent

                # Create orchestrator with template mocking
                with patch("chat.orchestrator.FileSystemLoader"):
                    with patch("chat.orchestrator.Environment") as mock_env_class:
                        mock_env = MagicMock()
                        mock_template = MagicMock()
                        mock_template.render.return_value = (
                            "Rendered prompt with history"
                        )
                        mock_env.get_template.return_value = mock_template
                        mock_env_class.return_value = mock_env

                        orchestrator = AgentOrchestrator(
                            session_manager=session_manager
                        )

                        # Set app state manually
                        test_app.state.session_manager = session_manager
                        test_app.state.orchestrator = orchestrator

                        # Override dependencies
                        def override_get_orchestrator():
                            return orchestrator

                        def override_get_session():
                            return {
                                "id": "test-session-123",
                                "metadata": {
                                    "user_id": "test-user-456",
                                    "correlation_id": "test-corr-789",
                                },
                            }

                        test_app.dependency_overrides[get_orchestrator] = (
                            override_get_orchestrator
                        )
                        test_app.dependency_overrides[get_session] = (
                            override_get_session
                        )

                        # Patch Runner to use FakeModel
                        with patch("chat.orchestrator.Runner") as mock_runner:
                            # Setup Runner.run to use FakeModel (async version)
                            async def run_with_fake_model(
                                starting_agent, input, context, run_config
                            ):
                                # Get the next output from fake model
                                output = fake_model.get_next_output()
                                if isinstance(output, Exception):
                                    raise output

                                # Create mock result
                                result = MagicMock()
                                # Extract text from output items
                                text_content = ""
                                for item in output:
                                    if hasattr(item, "type") and item.type == "message":
                                        for content in item.content:
                                            if hasattr(content, "text"):
                                                text_content += content.text
                                result.final_output = text_content or "Default response"

                                # Store what was sent to the model
                                fake_model.last_turn_args = {
                                    "system_instructions": starting_agent.instructions,
                                    "input": input,
                                    "tools": mock_tools,  # Pass the mock tools
                                }

                                return result

                            # Setup Runner.run_streamed for streaming tests
                            def run_streamed_with_fake_model(
                                starting_agent, input, context, run_config
                            ):
                                class MockStream:
                                    async def stream_events(self):
                                        output = fake_model.get_next_output()
                                        if isinstance(output, Exception):
                                            # Yield error event with correct structure
                                            yield type(
                                                "Event",
                                                (),
                                                {
                                                    "type": "error",
                                                    "data": {"error": str(output)},
                                                },
                                            )()
                                            return

                                        # Extract text content from output
                                        text_content = ""
                                        for item in output:
                                            if (
                                                hasattr(item, "type")
                                                and item.type == "message"
                                            ):
                                                for content in item.content:
                                                    if hasattr(content, "text"):
                                                        text_content += content.text

                                        # Yield raw_response_event with tool call (simulates agent thinking)
                                        yield type(
                                            "Event",
                                            (),
                                            {
                                                "type": "raw_response_event",
                                                "data": type(
                                                    "Data",
                                                    (),
                                                    {
                                                        "choices": [
                                                            type(
                                                                "Choice",
                                                                (),
                                                                {
                                                                    "delta": type(
                                                                        "Delta",
                                                                        (),
                                                                        {
                                                                            "tool_calls": [
                                                                                type(
                                                                                    "ToolCall",
                                                                                    (),
                                                                                    {
                                                                                        "id": "call_123",
                                                                                        "function": type(
                                                                                            "Function",
                                                                                            (),
                                                                                            {
                                                                                                "name": "semantic_search"
                                                                                            },
                                                                                        )(),
                                                                                    },
                                                                                )()
                                                                            ]
                                                                        },
                                                                    )()
                                                                },
                                                            )()
                                                        ]
                                                    },
                                                )(),
                                            },
                                        )()

                                        # Yield run_item_stream_event for tool completion
                                        yield type(
                                            "Event",
                                            (),
                                            {
                                                "type": "run_item_stream_event",
                                                "name": "tool_completed",
                                                "item": type(
                                                    "Item", (), {"id": "call_123"}
                                                )(),
                                            },
                                        )()

                                        # Yield raw_response_event with content chunks
                                        for chunk in ["Here's ", "your ", "answer"]:
                                            yield type(
                                                "Event",
                                                (),
                                                {
                                                    "type": "raw_response_event",
                                                    "data": type(
                                                        "Data",
                                                        (),
                                                        {
                                                            "choices": [
                                                                type(
                                                                    "Choice",
                                                                    (),
                                                                    {
                                                                        "delta": type(
                                                                            "Delta",
                                                                            (),
                                                                            {
                                                                                "content": chunk
                                                                            },
                                                                        )()
                                                                    },
                                                                )()
                                                            ]
                                                        },
                                                    )(),
                                                },
                                            )()

                                return MockStream()

                            mock_runner.run = AsyncMock(side_effect=run_with_fake_model)
                            mock_runner.run_streamed = MagicMock(
                                side_effect=run_streamed_with_fake_model
                            )

                            with TestClient(test_app) as client:
                                yield client, fake_model, test_app
