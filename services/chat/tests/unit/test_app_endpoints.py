# services/chat/tests/unit/test_app_endpoints.py
# Unit tests for FastAPI endpoints in app.py

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path to import helpers
sys.path.insert(0, str(Path(__file__).parent.parent))
from helpers import assert_response_format


@pytest.mark.unit
class TestChatEndpoint:
    """Unit tests for /chat endpoint."""

    def test_chat_endpoint_success(self, unit_test_client, sample_chat_request):
        """Test successful chat request."""
        response = unit_test_client.post("/chat", json=sample_chat_request)

        assert response.status_code == 200
        data = response.json()
        assert_response_format(data)
        assert data["message"] == "Test response from agent"

    def test_chat_endpoint_validation_error(self, unit_test_client):
        """Test request validation."""
        # Missing message field
        response = unit_test_client.post("/chat", json={})
        assert response.status_code == 422

        # Empty message
        response = unit_test_client.post("/chat", json={"message": ""})
        assert response.status_code in [200, 400]  # Depends on validation rules


# def test_chat_delegates_to_orchestrator(self, unit_test_client, mock_orchestrator):
#     mock_orchestrator.process_message.reset_mock()
#     unit_test_client.post("/chat", json={"message": "foo"})
#     mock_orchestrator.process_message.assert_called_once_with("foo", ANY)


@pytest.mark.unit
class TestStreamEndpoint:
    """Unit tests for /chat/stream endpoint."""

    def test_stream_endpoint_success(self, unit_test_client, sample_streaming_request):
        """Test successful streaming request."""
        # Use stream=True to avoid consuming the async generator in sync context
        with unit_test_client as client:
            response = client.post("/chat/stream", json=sample_streaming_request)

            assert response.status_code == 200
            assert (
                response.headers["content-type"] == "text/event-stream; charset=utf-8"
            )

            # Optionally read first chunk to verify it's SSE
            # chunk = next(response.iter_content(1024))
            # assert b"data:" in chunk

            response.close()

    def test_stream_endpoint_validation_error(self, unit_test_client):
        """Test streaming validation."""
        response = unit_test_client.post("/chat/stream", json={})
        assert response.status_code == 422


@pytest.mark.unit
class TestHealthEndpoint:
    """Unit tests for /health endpoint."""

    def test_health_endpoint_format(self, unit_test_client):
        """Test health endpoint response format."""
        response = unit_test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "status" in data
        assert "version" in data
        # assert "details" in data

        # # Check details structure #TODO: figure out orchestrator initialization and status w/ and w/o mcp connections
        # details = data["details"]
        # required_details = [
        #     "agent_ready",
        #     "agent_name",
        #     "model",
        #     "template_loaded",
        #     "tool_count",
        # ]
        # for field in required_details:
        #     assert field in details

    def test_health_endpoint_values(self, unit_test_client):
        """Test health endpoint values."""
        response = unit_test_client.get("/health")
        data = response.json()

        assert data["status"] == "ok"
        # assert data["details"]["agent_ready"] is True
        # assert data["details"]["agent_name"] == "EcomAssistant"
        # assert data["details"]["model"] == "gpt-4o-mini"


@pytest.mark.unit
class TestSessionManagement:
    """Unit tests for session management in endpoints."""

    def test_session_headers_used(self, unit_test_client):
        """Test that session headers are properly used."""
        # Instead of patching, we need to temporarily change the dependency override
        from chat.app import get_session

        # Create a custom override
        def custom_get_session():
            return {
                "id": "custom-session-id",
                "metadata": {"user_id": "custom-user", "correlation_id": "custom-corr"},
            }

        # Get the app from the test client
        app = unit_test_client.app

        # Temporarily replace the override
        original_override = app.dependency_overrides.get(get_session)
        app.dependency_overrides[get_session] = custom_get_session

        try:
            response = unit_test_client.post("/chat", json={"message": "test"})

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "custom-session-id"
            assert data["correlation_id"] == "custom-corr"
        finally:
            # Restore original override
            if original_override:
                app.dependency_overrides[get_session] = original_override
            else:
                app.dependency_overrides.pop(get_session, None)
