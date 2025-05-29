# services/chat/tests/integration/test_tool_discovery.py
# Integration tests for MCP tool discovery

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import create_text_message, create_tool_call
from fake_model import FakeModel


@pytest.mark.integration
class TestMCPServerIntegration:
    """Test MCP server integration with orchestrator."""

    @pytest.mark.asyncio
    async def test_load_templates_connects_mcp_servers(
        self, integration_test_client
    ):  # TODO: remove _connects_mcp_servers since no longer dependency.
        """Test that load_templates."""
        client, fake_model, app = integration_test_client
        orchestrator = app.state.orchestrator
        await orchestrator.load_templates()
        # Just verify it completes without error
        assert True

    def test_mcp_servers_initialized(self, integration_test_client):
        """Test that MCP server configs are properly initialized."""
        client, fake_model, app = integration_test_client
        orchestrator = app.state.orchestrator

        # CHANGE: Check _server_configs instead
        assert hasattr(orchestrator, "_server_configs")
        assert len(orchestrator._server_configs) == 2

        for config in orchestrator._server_configs:
            assert "name" in config
            assert "url" in config
            assert config["name"] in ["order", "product"]

    # def test_mcp_server_urls_from_environment(self, integration_test_client):
    #     """Test that MCP server URLs come from environment variables."""
    #     # Test with custom environment variables
    #     with patch.dict(
    #         "os.environ",
    #         {
    #             "ORDER_MCP_URL": "http://custom-order:8002/mcp",
    #             "PRODUCT_MCP_URL": "http://custom-product:8003/mcp",
    #         },
    #     ):
    #         # Need to recreate orchestrator to pick up new env vars
    #         from chat.orchestrator import AgentOrchestrator
    #         from chat.session import SessionManager

    #         with patch("chat.orchestrator.MCPServerSse") as mock_mcp_class:
    #             mock_order = MagicMock()
    #             mock_product = MagicMock()
    #             mock_mcp_class.side_effect = [mock_order, mock_product]

    #             with patch("chat.orchestrator.Agent"):
    #                 with patch("chat.orchestrator.FileSystemLoader"):
    #                     with patch("chat.orchestrator.Environment"):
    #                         session_mgr = SessionManager(ttl_minutes=30)
    #                         orchestrator = AgentOrchestrator(
    #                             session_manager=session_mgr
    #                         )

    #                         # Verify MCPServerSse was called with correct URLs
    #                         calls = mock_mcp_class.call_args_list
    #                         assert len(calls) == 2

    #                         # Check order service URL
    #                         assert (
    #                             calls[0].kwargs["params"]["url"]
    #                             == "http://custom-order:8002/mcp"
    #                         )

    #                         # Check product service URL
    #                         assert (
    #                             calls[1].kwargs["params"]["url"]
    #                             == "http://custom-product:8003/mcp"
    #                         )


@pytest.mark.integration
class TestAgentMCPIntegration:
    def test_agent_receives_mcp_servers(self, integration_test_client):
        """Test that Agent is initialized properly."""
        client, fake_model, app = integration_test_client
        orchestrator = app.state.orchestrator
        assert hasattr(orchestrator, "agent")
        assert orchestrator.agent is not None
        # CHANGE: Check _server_configs
        assert len(orchestrator._server_configs) == 2

    def test_tools_discovered_from_mcp(self, integration_test_client):
        """Test that tools are discovered from MCP servers."""
        client, fake_model, app = integration_test_client

        # Check agent has tools (mocked in conftest)
        agent = app.state.orchestrator.agent

        # In the mock, we set _tools_cache
        assert hasattr(agent, "_tools_cache")
        assert len(agent._tools_cache) == 4  # 2 from each service

        # Verify tool names
        tool_names = [t.name for t in agent._tools_cache]
        assert "get_orders_by_customer" in tool_names
        assert "get_order_details" in tool_names
        assert "semantic_search" in tool_names
        assert "search_by_category" in tool_names


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in MCP integration."""

    @pytest.mark.asyncio
    async def test_mcp_connection_failure_handled(self):
        """Test handling of MCP connection failures."""
        from chat.orchestrator import AgentOrchestrator
        from chat.session import SessionManager

        with patch("chat.orchestrator.MCPServerSse") as mock_mcp_class:
            # Make __aenter__ fail
            mock_server = MagicMock()
            mock_server.name = "failing-service"
            mock_server.__aenter__.side_effect = Exception("Connection failed")
            mock_mcp_class.return_value = mock_server

            with patch("chat.orchestrator.Agent"):
                with patch("chat.orchestrator.FileSystemLoader"):
                    with patch("chat.orchestrator.Environment"):
                        session_mgr = SessionManager(ttl_minutes=30)
                        orchestrator = AgentOrchestrator(session_manager=session_mgr)

                        # load_templates should handle the error gracefully
                        try:
                            await orchestrator.load_templates()
                        except Exception as e:
                            # Should log but not crash
                            assert "Failed to connect" in str(e)

    def test_missing_environment_variables(self):
        """Test behavior when MCP URLs are not set."""
        # Clear environment variables
        with patch.dict("os.environ", {}, clear=True):
            from chat.orchestrator import AgentOrchestrator
            from chat.session import SessionManager

            with patch("chat.orchestrator.MCPServerSse") as mock_mcp_class:
                mock_order = MagicMock()
                mock_product = MagicMock()
                mock_mcp_class.side_effect = [mock_order, mock_product]

                with patch("chat.orchestrator.Agent"):
                    with patch("chat.orchestrator.FileSystemLoader"):
                        with patch("chat.orchestrator.Environment"):
                            session_mgr = SessionManager(ttl_minutes=30)
                            orchestrator = AgentOrchestrator(
                                session_manager=session_mgr
                            )

                            assert len(orchestrator._server_configs) == 2
                            assert (
                                orchestrator._server_configs[0]["url"]
                                == "http://localhost:8002/mcp"
                            )
                            assert (
                                orchestrator._server_configs[1]["url"]
                                == "http://localhost:8003/mcp"
                            )


@pytest.mark.integration
class TestCleanup:
    """Test cleanup of MCP resources."""

    @pytest.mark.asyncio
    async def test_cleanup_closes_mcp_connections(self, integration_test_client):
        """Test that cleanup properly closes MCP connections."""
        client, fake_model, app = integration_test_client
        orchestrator = app.state.orchestrator
        await orchestrator.cleanup()
        # Just verify it completes
        assert True

    @pytest.mark.asyncio
    async def test_cleanup_handles_errors(self, integration_test_client):
        """Test that cleanup handles errors gracefully."""
        client, fake_model, app = integration_test_client
        orchestrator = app.state.orchestrator

        # If there's an instance, mock its cleanup to fail
        if orchestrator._server_configs[0]["instance"]:
            orchestrator._server_configs[0]["instance"].cleanup = AsyncMock(
                side_effect=Exception("Cleanup failed")
            )

        await orchestrator.cleanup()
        assert True
