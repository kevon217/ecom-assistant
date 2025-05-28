# services/chat/tests/helpers.py
# Test utilities and helpers

from typing import Any, List
from unittest.mock import AsyncMock, MagicMock

from agents.items import ResponseOutputItem, ResponseStreamEvent
from fake_model import FakeModel


class AsyncEventStream:
    """Mock async event stream for testing streaming endpoints."""

    def __init__(self, events: List[dict]):
        self.events = events

    async def stream_events(self):
        """Async generator yielding events."""
        for event in self.events:
            # Create mock event with correct structure for our app
            mock_event = MagicMock()
            mock_event.type = event.get("type")

            # Create mock data structure for raw_response_event
            if event.get("type") == "raw_response_event":
                mock_event.data = type(
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
                                        {"content": event.get("content", "")},
                                    )()
                                },
                            )()
                        ]
                    },
                )()
            else:
                mock_event.data = event.get("data", {})

            yield mock_event


def create_mock_runner_for_unit_tests():
    """Create a properly mocked Runner for unit tests."""
    mock_runner = MagicMock()

    # Mock run - returns result directly (async)
    async def mock_run(*args, **kwargs):
        mock_result = MagicMock()
        mock_result.final_output = "Test response from agent"
        return mock_result

    mock_runner.run = AsyncMock(side_effect=mock_run)

    # Mock run_streamed - returns sync stream object
    def mock_run_streamed(*args, **kwargs):
        return AsyncEventStream(
            [
                {"type": "raw_response_event", "content": "Processing..."},
                {"type": "raw_response_event", "content": "Found 2 items"},
            ]
        )

    mock_runner.run_streamed = MagicMock(side_effect=mock_run_streamed)

    return mock_runner


def assert_response_format(response_data: dict):
    """Assert that a chat response has the correct format."""
    required_fields = ["message", "session_id", "correlation_id", "duration_ms"]
    for field in required_fields:
        assert field in response_data, f"Missing required field: {field}"

    assert isinstance(response_data["message"], str)
    assert isinstance(response_data["session_id"], str)
    assert isinstance(response_data["correlation_id"], str)
    assert isinstance(response_data["duration_ms"], (int, float))
    assert response_data["duration_ms"] >= 0


def create_fake_model_with_tools(
    tool_responses: List[List[ResponseOutputItem]],
) -> FakeModel:
    """Create a FakeModel pre-configured with tool call responses."""
    fake_model = FakeModel()
    fake_model.add_multiple_turn_outputs(tool_responses)
    return fake_model
