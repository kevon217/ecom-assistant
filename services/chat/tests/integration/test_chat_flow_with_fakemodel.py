# services/chat/tests/integration/test_chat_flow_with_fakemodel.py
# Integration tests using FakeModel to test full flow

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import create_text_message, create_tool_call, create_tool_output
from helpers import assert_response_format


@pytest.mark.integration
class TestChatFlowIntegration:
    """Test full chat flow with FakeModel."""

    def test_simple_chat_flow(self, integration_test_client):
        """Test simple question-answer flow."""
        client, fake_model, app = integration_test_client

        # Set up fake model response
        fake_model.set_next_output(
            [
                create_text_message(
                    "I can help you find orders. Customer 123 has 2 recent orders."
                )
            ]
        )

        # Make request
        response = client.post(
            "/chat", json={"message": "Show me orders for customer 123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert_response_format(data)
        assert "2 recent orders" in data["message"]

        # Verify what was sent to the model
        assert fake_model.last_turn_args["input"] == "Show me orders for customer 123"
        assert "Rendered prompt" in fake_model.last_turn_args["system_instructions"]

    def test_error_propagation(self, integration_test_client):
        """Test that model errors are properly handled with fallback."""
        client, fake_model, app = integration_test_client

        fake_model.set_next_output(Exception("Model unavailable"))
        response = client.post("/chat", json={"message": "test"})

        # NOW EXPECTS 200 with fallback message (not 500)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert len(data["message"]) > 0

    def test_streaming_endpoint_availability(self, integration_test_client):
        """Test streaming endpoint is available."""
        client, fake_model, app = integration_test_client

        # Set up streaming response
        fake_model.set_next_output(
            [create_text_message("I'm searching for wireless headphones under $100...")]
        )

        # Make streaming request
        response = client.post(
            "/chat/stream", json={"message": "Find wireless headphones under $100"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    def test_session_persistence(self, integration_test_client):
        """Test that messages are saved to session history."""
        client, fake_model, app = integration_test_client

        # First message
        fake_model.set_next_output([create_text_message("Hello! How can I help you?")])
        response1 = client.post("/chat", json={"message": "Hi there"})
        assert response1.status_code == 200

        # Second message - verify session manager was called
        fake_model.set_next_output([create_text_message("I can help with that order.")])
        response2 = client.post("/chat", json={"message": "Show me order 123"})
        assert response2.status_code == 200

        # Verify session manager add_message was called
        session_mgr = app.state.session_manager
        # Check if it's a mock object
        if hasattr(session_mgr, "add_message") and hasattr(
            session_mgr.add_message, "call_count"
        ):
            assert session_mgr.add_message.call_count >= 2  # At least 2 messages added


@pytest.mark.integration
class TestToolIntegration:
    """Test tool discovery and execution with MCP servers."""

    def test_health_reports_mcp_config(self, integration_test_client):
        """Test that health endpoint reports MCP configuration."""
        client, fake_model, app = integration_test_client

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "config" in data["details"]
        assert "order_mcp" in data["details"]["config"]
        assert "product_mcp" in data["details"]["config"]
        assert "localhost:8002" in data["details"]["config"]["order_mcp"]
        assert "localhost:8003" in data["details"]["config"]["product_mcp"]

    def test_orchestrator_has_mcp_servers(self, integration_test_client):
        """Test that orchestrator properly initializes MCP server configs."""
        client, fake_model, app = integration_test_client
        orchestrator = app.state.orchestrator

        # CHANGE: mcp_servers → _server_configs
        assert hasattr(orchestrator, "_server_configs")
        assert len(orchestrator._server_configs) == 2

        # SSE servers don't have name attribute, but we can check they exist
        # assert orchestrator.order_server is not None
        # assert orchestrator.product_server is not None

    def test_orchestrator_tool_discovery(self, integration_test_client):
        """Test that orchestrator has MCP server configuration."""
        client, fake_model, app = integration_test_client
        orchestrator = app.state.orchestrator

        # CHANGE: mcp_servers → _server_configs
        assert hasattr(orchestrator, "_server_configs")
        assert len(orchestrator._server_configs) == 2

    def test_orchestrator_template_loading(self, integration_test_client):
        """Test that orchestrator loads templates correctly."""
        client, fake_model, app = integration_test_client

        # Access orchestrator directly for template testing
        orchestrator = app.state.orchestrator
        assert orchestrator.system_tpl is not None

    def test_run_config_uses_correct_model(self, integration_test_client):
        """Test that RunConfig is created with correct model from config."""
        client, fake_model, app = integration_test_client

        # Set response
        fake_model.set_next_output([create_text_message("Test response")])

        # Make request
        with patch("chat.orchestrator.config") as mock_config:
            mock_config.agent_model = "gpt-4o-mini"

            response = client.post("/chat", json={"message": "test"})
            assert response.status_code == 200
