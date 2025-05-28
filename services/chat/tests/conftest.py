# services/chat/tests/conftest.py
# Root level fixtures shared by all tests

import json
import os
import sys
from pathlib import Path
from typing import List

import pytest

os.environ["TESTING"] = "true"


# Set up Python path for testing
def setup_python_path():
    """Set up Python path to allow imports from both service and shared libs."""
    chat_root = Path(__file__).parent.parent.absolute()
    chat_src = chat_root / "src"
    project_root = chat_root.parent.parent.absolute()
    libs_path = project_root / "libs"

    paths_to_add = [str(chat_src), str(libs_path), str(project_root)]
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)


setup_python_path()

# Import after path setup
from agents.items import (
    FunctionCallOutput,
    ResponseFunctionToolCall,
    ResponseInputItemParam,
    ResponseOutputMessage,
    ResponseOutputText,
)

# ============== Test Data Factories ==============


def create_text_message(content: str, role: str = "assistant") -> ResponseOutputMessage:
    """Create a text message output item."""
    return ResponseOutputMessage(
        id="msg_" + str(hash(content))[:8],  # Generate a unique ID
        role=role,
        content=[ResponseOutputText(text=content, type="output_text", annotations=[])],
        type="message",
        status="completed",  # Add required status field
    )


def create_tool_call(
    tool_name: str, call_id: str = None, args: dict = None
) -> ResponseFunctionToolCall:
    """Create a function tool call."""
    return ResponseFunctionToolCall(
        call_id=call_id or f"call_{tool_name}_123",
        name=tool_name,
        arguments=json.dumps(args or {}),
        type="function",
    )


def create_tool_output(call_id: str, output: str) -> FunctionCallOutput:
    """Create a function call output."""
    return {"call_id": call_id, "output": output, "type": "function_call_output"}


def create_user_message(content: str) -> ResponseInputItemParam:
    """Create a user input message."""
    return {"role": "user", "content": content}


# ============== Common Fixtures ==============


@pytest.fixture
def sample_session_data():
    """Sample session data for testing."""
    return {
        "id": "test-session-123",
        "metadata": {"user_id": "test-user-456", "correlation_id": "test-corr-789"},
    }


@pytest.fixture
def sample_chat_request():
    """Sample chat request payload."""
    return {"message": "Show me recent orders for customer 123"}


@pytest.fixture
def sample_streaming_request():
    """Sample streaming request payload."""
    return {"message": "Find wireless headphones under $100"}


# ============== Test Context Fixtures ==============


@pytest.fixture
def test_app_context():
    """Create test AppContext."""
    from libs.ecom_shared.context import AppContext

    return AppContext(
        user_id="test-user-456",
        correlation_id="test-corr-789",
        session_id="test-session-123",
        request_id="test-request-123",
    )


@pytest.fixture
def test_runner_context():
    """Create test RunnerContext."""
    from agents_mcp import RunnerContext

    return RunnerContext(
        session_id="test-session-123",
        user_id="test-user-456",
        correlation_id="test-corr-789",
        request_id="test-request-123",
    )
