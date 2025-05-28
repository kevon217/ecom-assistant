# libs/ecom_shared/guardrails.py
"""
Guardrails and safety mechanisms for input validation and security.
"""


class GuardrailViolation(Exception):
    """
    Exception raised when input violates safety guardrails.

    This can include:
    - Inappropriate content
    - Injection attempts
    - Rate limiting violations
    - Input validation failures
    """

    def __init__(self, message: str, violation_type: str = "general"):
        self.message = message
        self.violation_type = violation_type
        super().__init__(self.message)

    def __str__(self):
        return f"Guardrail violation ({self.violation_type}): {self.message}"


def validate_input_length(text: str, max_length: int = 10000) -> None:
    """
    Validate that input text doesn't exceed maximum length.

    Args:
        text: Input text to validate
        max_length: Maximum allowed length

    Raises:
        GuardrailViolation: If text exceeds maximum length
    """
    if len(text) > max_length:
        raise GuardrailViolation(
            f"Input text too long: {len(text)} characters (max: {max_length})",
            violation_type="length",
        )


def validate_query_safety(query: str) -> None:
    """
    Basic safety validation for search queries.

    Args:
        query: Search query to validate

    Raises:
        GuardrailViolation: If query contains unsafe content
    """
    # Basic checks - expand as needed
    dangerous_patterns = [
        "<script",
        "javascript:",
        "eval(",
        "exec(",
    ]

    query_lower = query.lower()
    for pattern in dangerous_patterns:
        if pattern in query_lower:
            raise GuardrailViolation(
                f"Query contains potentially unsafe content: {pattern}",
                violation_type="injection",
            )


"""
Guardrail rules for agent input and output validation.

This module provides declarative guardrail rules using the Agents SDK
for validating inputs and outputs in a consistent way.

TODO(v0.9): This is a placeholder with basic rules. Full implementation
will be completed in v0.9 when we integrate comprehensive guardrails.
"""

import re
from typing import Any, Dict, List, Optional, Pattern

try:
    from agents import GuardrailViolation, InputGuard, OutputGuard
except ImportError:
    # Fallback classes when SDK is not available
    class GuardrailViolation(Exception):
        def __init__(self, message: str, rule: str):
            self.message = message
            self.rule = rule
            super().__init__(message)

    class InputGuard:
        def __init__(self, rules: List[Dict[str, Any]]):
            self.rules = rules

        def validate(self, input_text: str) -> Optional[GuardrailViolation]:
            return None

    class OutputGuard:
        def __init__(self, rules: List[Dict[str, Any]]):
            self.rules = rules

        def validate(self, output_text: str) -> Optional[GuardrailViolation]:
            return None


# Common injection patterns to block
INJECTION_PATTERNS: List[Pattern] = [
    # Prompt injection attempts
    re.compile(r"ignore previous instructions", re.IGNORECASE),
    re.compile(r"ignore all previous instructions", re.IGNORECASE),
    re.compile(r"disregard .+ instructions", re.IGNORECASE),
    re.compile(r"do not follow .+ instructions", re.IGNORECASE),
    # System prompt leaking attempts
    re.compile(r"print your instructions", re.IGNORECASE),
    re.compile(r"output your system prompt", re.IGNORECASE),
    re.compile(r"tell me your prompt", re.IGNORECASE),
    re.compile(r"show me your code", re.IGNORECASE),
    # Data exfiltration attempts
    re.compile(r"send (data|information) to", re.IGNORECASE),
    re.compile(r"upload .+ to (url|website|server)", re.IGNORECASE),
]


# Define input guardrail rules
INPUT_RULES = [
    # Max token limit for user input
    {
        "type": "token_limit",
        "max_tokens": 1000,
        "violation_message": "Your message exceeds the maximum allowed length. Please shorten your message and try again.",
    },
    # No empty input
    {
        "type": "required_text",
        "violation_message": "Please provide a message before submitting.",
    },
    # Block injection patterns
    {
        "type": "blocked_patterns",
        "patterns": [pattern.pattern for pattern in INJECTION_PATTERNS],
        "violation_message": "Your message contains disallowed instructions or patterns. Please revise and try again.",
    },
]


# Define output guardrail rules
OUTPUT_RULES = [
    # Prevent excessive output
    {
        "type": "token_limit",
        "max_tokens": 2000,
        "violation_message": "The response exceeded the maximum allowed length and was truncated.",
    },
    # Prevent leaking system instructions
    {
        "type": "blocked_patterns",
        "patterns": [
            r"as an AI assistant",
            r"my instructions",
            r"system prompt",
            r"I've been instructed to",
        ],
        "violation_message": "The response contained inappropriate content and was filtered.",
    },
]


# Create guardrail instances
input_guard = InputGuard(INPUT_RULES)
output_guard = OutputGuard(OUTPUT_RULES)


def validate_input(input_text: str) -> Optional[GuardrailViolation]:
    """
    Validate user input against defined guardrail rules.

    Args:
        input_text: The input text to validate

    Returns:
        GuardrailViolation if rules are violated, None otherwise
    """
    return input_guard.validate(input_text)


def validate_output(output_text: str) -> Optional[GuardrailViolation]:
    """
    Validate agent output against defined guardrail rules.

    Args:
        output_text: The output text to validate

    Returns:
        GuardrailViolation if rules are violated, None otherwise
    """
    return output_guard.validate(output_text)


def handle_guardrail_violation(violation: GuardrailViolation) -> str:
    """
    Generate a user-friendly message for guardrail violations.

    Args:
        violation: The guardrail violation

    Returns:
        User-friendly error message
    """
    return f"I'm unable to process that: {violation.message}"
