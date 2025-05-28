# libs/ecom_shared/context.py
"""
Application context models for request tracking and session management.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AppContext:
    """
    Application context that carries request-level information
    across the application stack.

    Used with OpenAI Agents SDK RunContextWrapper.
    """

    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert context to dictionary for logging/serialization."""
        return {
            "user_id": self.user_id,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
        }
