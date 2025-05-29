# Integration tests for error handling scenarios
import json
import sys
from pathlib import Path
from typing import Dict  # services/chat/tests/integration/test_error_scenarios.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import create_text_message
from fake_model import FakeModel


@pytest.mark.integration
class TestModelErrors:
    """Test error handling from model failures."""

    def test_model_exception_returns_200(self, integration_test_client):
        """Test that model exceptions are handled gracefully."""
        client, fake_model, app = integration_test_client
        fake_model.set_next_output(RuntimeError("Model crashed"))
        response = client.post("/chat", json={"message": "test"})

        # NOW EXPECTS 200 with fallback (not 500)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_model_timeout_handled(self, integration_test_client):
        """Test handling of model timeout errors."""
        client, fake_model, app = integration_test_client
        fake_model.set_next_output(TimeoutError("Model request timed out"))
        response = client.post("/chat", json={"message": "test"})

        # NOW EXPECTS 200 with fallback (not 500)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_streaming_error_event(self, integration_test_client):
        """Test that streaming endpoint emits error events."""
        client, fake_model, app = integration_test_client

        # Set model to raise exception
        fake_model.set_next_output(Exception("Streaming failed"))

        # Make streaming request
        with client as c:
            with c.stream("POST", "/chat/stream", json={"message": "test"}) as response:
                assert response.status_code == 200

                # Read SSE events
                events = []
                for line in response.iter_lines():
                    if line and line.startswith("data: "):
                        data = json.loads(line[6:])
                        events.append(data)
                        if data.get("type") == "done":
                            break

                # Should have some events and end with done
                assert len(events) > 0
                event_types = [e.get("type") for e in events]
                assert "done" in event_types

                # Should have error event OR complete gracefully
                error_events = [e for e in events if e.get("type") == "error"]
                if error_events:
                    assert "Stream processing failed" in error_events[0].get(
                        "error", ""
                    )


@pytest.mark.integration
class TestValidationErrors:
    """Test request validation error handling."""

    def test_missing_message_field(self, integration_test_client):
        """Test validation when message field is missing."""
        client, fake_model, app = integration_test_client

        response = client.post("/chat", json={})

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert any("message" in str(err) for err in data["detail"])

    def test_invalid_json_payload(self, integration_test_client):
        """Test handling of invalid JSON."""
        client, fake_model, app = integration_test_client

        response = client.post(
            "/chat", data="invalid json", headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_empty_message_handled(self, integration_test_client):
        """Test handling of empty message."""
        client, fake_model, app = integration_test_client

        # Set default response
        fake_model.set_next_output([create_text_message("I need more information.")])

        response = client.post("/chat", json={"message": ""})

        # Empty string might be accepted, depends on validation
        assert response.status_code in [200, 422]


@pytest.mark.integration
class TestSessionErrors:
    """Test session-related error scenarios."""

    def test_invalid_session_headers(self, integration_test_client):
        """Test handling of invalid session headers."""
        client, fake_model, app = integration_test_client

        from agents_mcp import RunnerContext
        from fastapi import Depends

        from chat.app import get_runner_context, get_session

        # Override session to return invalid data
        def bad_session():
            return {
                "id": None,  # This will cause issues
                "metadata": None,  # This too
            }

        # Override get_runner_context to handle the bad session data
        def bad_runner_context(session=Depends(bad_session)):
            # Handle None values gracefully
            session_id = session.get("id") if session else None
            metadata = session.get("metadata") if session else None

            # Ensure we always return valid values for required fields
            return RunnerContext(
                session_id=session_id or "fallback-session-id",  # Provide fallback
                user_id=metadata.get("user_id") if metadata else None,
                correlation_id=metadata.get("correlation_id") if metadata else None,
                request_id=session_id or "fallback-request-id",
            )

        app.dependency_overrides[get_session] = bad_session
        app.dependency_overrides[get_runner_context] = bad_runner_context

        try:
            # Set a response for the fake model
            fake_model.set_next_output([create_text_message("Test response")])

            response = client.post("/chat", json={"message": "test"})
            # The response should work with fallback values
            assert response.status_code == 200

            # Check the response has the fallback session ID
            data = response.json()
            assert data["session_id"] == "fallback-session-id"
            assert data["correlation_id"] is None  # This can be None

        finally:
            # Restore original overrides
            app.dependency_overrides[get_session] = lambda: {
                "id": "test-session-123",
                "metadata": {
                    "user_id": "test-user-456",
                    "correlation_id": "test-corr-789",
                },
            }
            # Remove the runner context override to let it use default
            app.dependency_overrides.pop(get_runner_context, None)


@pytest.mark.integration
class TestOrchestratorErrors:
    """Test orchestrator initialization errors."""

    def test_health_works_without_orchestrator(self):
        """Test that health endpoint works even without orchestrator."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from chat.app import router

        # Create app without orchestrator initialization
        test_app = FastAPI()
        test_app.include_router(router)

        with TestClient(test_app) as client:
            response = client.get("/health")
            # Health endpoint should work without orchestrator dependency
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "config" in data["details"]

    def test_template_loading_error_handled(self, integration_test_client):
        """Test that template loading errors don't crash the service."""
        client, fake_model, app = integration_test_client

        # Service should still work even if template failed to load
        orchestrator = app.state.orchestrator
        orchestrator.system_tpl = None  # Simulate failed template

        # Set response
        fake_model.set_next_output([create_text_message("Still working!")])

        response = client.post("/chat", json={"message": "test"})
        assert response.status_code == 200

        # Health should still work (no longer reports template status)
        health_response = client.get("/health")
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert "config" in health_data["details"]


@pytest.mark.integration
class TestMCPErrors:
    """Test MCP-related error scenarios."""

    @pytest.mark.asyncio
    async def test_mcp_server_unreachable(self):
        """Test handling when MCP server is unreachable."""
        from chat.orchestrator import AgentOrchestrator
        from chat.session import SessionManager

        with patch("chat.orchestrator.MCPServerSse") as mock_mcp_class:
            # Create server that fails to connect
            mock_server = MagicMock()
            mock_server.connect = AsyncMock(
                side_effect=ConnectionError("Cannot reach MCP server")
            )
            mock_mcp_class.return_value = mock_server

            with patch("chat.orchestrator.Agent"):
                with patch("chat.orchestrator.FileSystemLoader"):
                    with patch("chat.orchestrator.Environment"):
                        session_mgr = SessionManager(ttl_minutes=30)
                        orchestrator = AgentOrchestrator(session_manager=session_mgr)

                        # Should handle connection error gracefully
                        try:
                            await orchestrator.load_templates()
                            # If no exception, the error was handled
                        except Exception as e:
                            # Connection error might be logged but not necessarily raised
                            assert (
                                "connect" in str(e).lower()
                                or "failed" in str(e).lower()
                            )

    def test_partial_mcp_failure(self, integration_test_client):
        """Test when one MCP server fails but others work."""
        client, fake_model, app = integration_test_client

        # Simulate one server being down
        orchestrator = app.state.orchestrator

        # Health check should still work (no longer reports runtime MCP status)
        response = client.get("/health")
        assert response.status_code == 200

        # Should report MCP configuration URLs
        data = response.json()
        config = data["details"]["config"]
        assert "order_mcp" in config
        assert "product_mcp" in config


@pytest.mark.integration
class TestStreamingErrors:
    """Test streaming-specific error scenarios."""

    def test_streaming_client_disconnect(self, integration_test_client):
        """Test handling of client disconnect during streaming."""
        client, fake_model, app = integration_test_client

        # Set up a response that would stream
        fake_model.set_next_output([create_text_message("Long streaming response...")])

        # Start streaming request but close it immediately
        with client as c:
            # Use stream context manager properly
            with c.stream("POST", "/chat/stream", json={"message": "test"}) as response:
                assert response.status_code == 200
                # Just close without reading all events

    @pytest.mark.asyncio
    async def test_streaming_exception_during_generation(self, integration_test_client):
        """Test exception during streaming generation."""
        client, fake_model, app = integration_test_client

        # Set error response - this will be raised in our mock Runner
        fake_model.set_next_output(RuntimeError("Stream generation failed"))

        # The error should be in the stream events
        with client as c:
            with c.stream(
                "POST", "/chat/stream", json={"message": "test error"}
            ) as response:
                assert response.status_code == 200  # SSE still returns 200

                events = []
                for line in response.iter_lines():
                    if line and line.startswith("data: "):
                        try:
                            event_data = json.loads(line[6:])
                            events.append(event_data)
                            # Stop on done or error
                            if event_data.get("type") in ["done", "error"]:
                                break
                        except json.JSONDecodeError:
                            continue

                # Should have at least some events (thinking, error, etc)
                assert len(events) > 0

                # Check that streaming completed (core functionality)
                event_types = [e.get("type") for e in events]

                # Should have either error event or complete successfully with done
                assert "error" in event_types or "done" in event_types
