# services/chat/tests/unit/test_orchestrator.py
# Updated sections for SSE compatibility

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from libs.ecom_shared.context import AppContext


@pytest.mark.unit
class TestOrchestratorInitialization:
    """Test orchestrator initialization."""

    def test_orchestrator_creates_agent(self, mock_agent_class, mock_session_manager):
        """Test that orchestrator creates an Agent with correct parameters."""
        # Import after patching
        from chat.orchestrator import AgentOrchestrator

        # Mock MCP servers and template loading
        with patch("chat.orchestrator.MCPServerSse") as mock_mcp_class:
            # Create mock MCP servers
            mock_order_server = MagicMock()
            mock_order_server.connect = AsyncMock()
            mock_order_server.cleanup = AsyncMock()

            mock_product_server = MagicMock()
            mock_product_server.connect = AsyncMock()
            mock_product_server.cleanup = AsyncMock()

            mock_mcp_class.side_effect = [mock_order_server, mock_product_server]

            with patch("chat.orchestrator.FileSystemLoader"):
                with patch("chat.orchestrator.Environment") as mock_env_class:
                    mock_env = MagicMock()
                    mock_env.get_template.return_value = MagicMock()
                    mock_env_class.return_value = mock_env

                    orch = AgentOrchestrator(session_manager=mock_session_manager)

                    # Verify Agent was created
                    mock_agent_class.assert_called_once()

                    # Get the actual call arguments
                    call_args = mock_agent_class.call_args

                    # Check positional or keyword arguments
                    if call_args.args:
                        # Positional arguments used
                        assert len(call_args.args) >= 2
                    else:
                        # Keyword arguments used
                        assert call_args.kwargs["name"] == "EcomAssistant"
                        assert "instructions" in call_args.kwargs
                        assert "mcp_servers" in call_args.kwargs
                        assert len(call_args.kwargs["mcp_servers"]) == 2

                    # Verify orchestrator stores references
                    assert orch.session_manager is mock_session_manager
                    assert orch.agent is not None


@pytest.mark.unit
class TestLoadTemplates:
    """Test template loading and MCP connection."""

    @pytest.mark.asyncio
    async def test_load_templates_connects_mcp_servers(self, orchestrator_with_mocks):
        """Test that load_templates establishes MCP connections."""
        # Should complete without error
        await orchestrator_with_mocks.load_templates()

        # Verify connect was called on each server
        for server in orchestrator_with_mocks.mcp_servers:
            server.connect.assert_called_once()


@pytest.mark.unit
class TestCleanup:
    """Test cleanup of MCP resources."""

    @pytest.mark.asyncio
    async def test_cleanup_closes_mcp_connections(self, orchestrator_with_mocks):
        """Test that cleanup properly closes MCP connections."""
        orch = orchestrator_with_mocks

        # Call cleanup
        await orch.cleanup()

        # Verify cleanup was called on each server
        for server in orch.mcp_servers:
            server.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_handles_errors(self, orchestrator_with_mocks):
        """Test that cleanup handles errors gracefully."""
        orch = orchestrator_with_mocks

        # Make one server fail during cleanup
        orch.mcp_servers[0].cleanup.side_effect = Exception("Cleanup failed")

        # Should not raise exception
        await orch.cleanup()

        # Both servers should have cleanup attempted
        for server in orch.mcp_servers:
            server.cleanup.assert_called()


@pytest.mark.unit
class TestHealthStatus:
    """Test health status reporting."""

    def test_health_status_values(self, orchestrator_with_mocks):
        """Test health status values are correct."""
        orch = orchestrator_with_mocks

        with patch("chat.orchestrator.config") as mock_config:
            mock_config.agent_model = "gpt-4o-mini"

            status = orch.get_health_status()

            assert status["agent_ready"] is True
            assert status["agent_name"] == "EcomAssistant"
            assert status["model"] == "gpt-4o-mini"
            assert status["template_loaded"] is True
            # MCP servers should be listed
            assert "mcp_servers" in status
            assert "order-service" in status["mcp_servers"]
            assert "product-service" in status["mcp_servers"]
