# services/chat/tests/unit/conftest.py

# Unit test specific fixtures - focus on isolation with mocks

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path to import helpers
sys.path.insert(0, str(Path(__file__).parent.parent))
from helpers import create_mock_runner_for_unit_tests


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager for unit testing."""
    mock = MagicMock()
    mock.get_history.return_value = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    mock.add_message = MagicMock()
    return mock


@pytest.fixture
def mock_agent_class():
    """Mock Agent class for patching."""
    with patch("chat.orchestrator.Agent") as mock_class:
        mock_instance = MagicMock()
        mock_instance.name = "EcomAssistant"
        mock_instance.instructions = "You are an E-commerce Assistant. Help users find products and check orders."
        mock_instance.tools = []  # Initialize with empty tools list
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def mock_agent():
    """Mock Agent instance for unit testing."""
    mock = MagicMock()
    mock.name = "EcomAssistant"
    mock.instructions = "You are an E-commerce Assistant"
    mock.tools = []  # Always initialize tools attribute
    return mock


@pytest.fixture
def mock_runner():
    """Mock Runner for unit testing."""
    with patch("agents.Runner", create_mock_runner_for_unit_tests()):
        yield


@pytest.fixture
def orchestrator_with_mocks(mock_agent_class, mock_session_manager):
    """Create a real orchestrator with mocked dependencies."""
    # Import after patching
    from chat.orchestrator import AgentOrchestrator

    # Mock the MCP servers
    with patch("chat.orchestrator.MCPServerSse") as mock_mcp_class:
        # Create mock MCP server instances
        mock_order_server = MagicMock()
        mock_order_server.connect = AsyncMock()
        mock_order_server.cleanup = AsyncMock()

        mock_product_server = MagicMock()
        mock_product_server.connect = AsyncMock()
        mock_product_server.cleanup = AsyncMock()

        # Make the class return our mocks in order
        mock_mcp_class.side_effect = [mock_order_server, mock_product_server]

        # Mock the template loading
        with patch("chat.orchestrator.FileSystemLoader") as mock_loader:
            with patch("chat.orchestrator.Environment") as mock_env_class:
                mock_env = MagicMock()
                mock_template = MagicMock()
                mock_template.render.return_value = "Rendered prompt"
                mock_env.get_template.return_value = mock_template
                mock_env_class.return_value = mock_env

                orch = AgentOrchestrator(session_manager=mock_session_manager)
                return orch


@pytest.fixture
def mock_orchestrator(mock_agent, mock_session_manager):
    """Create a fully mocked orchestrator."""
    mock_orch = MagicMock()
    mock_orch.session_manager = mock_session_manager
    mock_orch.agent = mock_agent
    mock_orch.get_health_status.return_value = {
        "agent_ready": True,
        "agent_name": "EcomAssistant",
        "model": "gpt-4o-mini",
        "template_loaded": True,
        "tool_count": 0,
        "mcp_servers": ["order-service", "product-service"],
    }
    mock_orch.load_templates = AsyncMock()
    mock_orch.cleanup = AsyncMock()

    # Add template mock
    mock_orch.system_tpl = MagicMock()
    mock_orch.system_tpl.render.return_value = "Rendered prompt"

    # Add _render_prompt method
    mock_orch._render_prompt = MagicMock(return_value="Rendered prompt")

    # Add process_message method (async)
    async def mock_process_message(*args, **kwargs):
        return "Test response from agent"

    mock_orch.process_message = AsyncMock(side_effect=mock_process_message)

    # Add process_message_streaming method that returns a proper async generator
    class MockStream:
        async def stream_events(self):
            # Yield a raw_response_event with correct structure
            event = MagicMock()
            event.type = "raw_response_event"
            event.data = type(
                "Data",
                (),
                {
                    "choices": [
                        type(
                            "Choice",
                            (),
                            {
                                "delta": type(
                                    "Delta", (), {"content": "Test streaming"}
                                )()
                            },
                        )()
                    ]
                },
            )()
            yield event

    def mock_streaming(*args, **kwargs):
        return MockStream()

    mock_orch.process_message_streaming = MagicMock(side_effect=mock_streaming)

    # Add get_tool_friendly_name method
    mock_orch.get_tool_friendly_name = MagicMock(side_effect=lambda x: f"Using {x}")

    return mock_orch


@pytest.fixture
def unit_test_client(mock_orchestrator, mock_session_manager):
    """TestClient with all dependencies mocked for unit testing."""
    # Import Runner mock helper
    mock_runner = create_mock_runner_for_unit_tests()

    # Patch all dependencies with fresh mocks for each test
    # Note: Runner is now only imported in orchestrator.py
    with patch("chat.orchestrator.Runner", mock_runner):
        with patch("chat.app.SessionStore") as mock_session_store:
            mock_session_store.initialize = MagicMock()
            mock_session_store.flush = AsyncMock()

            with patch("chat.app.SessionManager") as mock_session_manager_class:
                mock_session_manager_class.return_value = mock_session_manager

                with patch("chat.app.AgentOrchestrator") as mock_orch_class:
                    mock_orch_class.return_value = mock_orchestrator

                    # Import create_app function and create a fresh app
                    from chat.app import create_app, get_orchestrator, get_session

                    # Create a new app instance
                    test_app = create_app()

                    # Override the dependencies
                    def override_get_orchestrator():
                        return mock_orchestrator

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
                    test_app.dependency_overrides[get_session] = override_get_session

                    # Create test client
                    with TestClient(test_app) as client:
                        yield client

                    # Clean up
                    test_app.dependency_overrides.clear()


@pytest.fixture
def test_client_with_mocks(mock_runner):
    """Test client with Runner mocked but other components real."""
    with patch("chat.app.SessionStore") as mock_session_store:
        mock_session_store.initialize = MagicMock()
        mock_session_store.flush = AsyncMock()

        # Import and create app
        from chat.app import create_app, get_session

        test_app = create_app()

        # Override session dependency
        def override_get_session():
            return {
                "id": "test-session-123",
                "metadata": {
                    "user_id": "test-user-456",
                    "correlation_id": "test-corr-789",
                },
            }

        test_app.dependency_overrides[get_session] = override_get_session

        with TestClient(test_app) as client:
            yield client

        test_app.dependency_overrides.clear()


@pytest.fixture
def dummy_tool():
    """Create a dummy tool for testing."""
    tool = MagicMock()
    tool.name = "semantic_search"
    tool.description = "Search for products"
    return tool
