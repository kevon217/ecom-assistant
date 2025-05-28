# services/chat/src/chat/models.py

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

## TOOL CALL MODELS ##


class ToolCall(BaseModel):
    """Information about a tool call made during chat processing."""

    name: str
    args: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None


## CHAT MODELS ##


class ChatRequest(BaseModel):
    """
    Request model for chat endpoints.

    Contains the message and optional session/config information.
    """

    message: str
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    run_config: Optional[Any] = None


class ChatResponse(BaseModel):
    """
    Response model for chat endpoints.

    Contains the response message and additional metadata.
    """

    message: str
    session_id: str
    correlation_id: Optional[str] = None
    duration_ms: Optional[float] = None
    # tool_calls: Optional[List[ToolCall]] = None
