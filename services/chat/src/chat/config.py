"""Chat service configuration."""

from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class ChatConfig(BaseSettings):
    """Chat service specific configuration."""

    # Service settings
    port: int = Field(8001, env="PORT")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # Session settings
    session_ttl_minutes: int = Field(60, env="CHAT_SESSION_TTL")
    session_store_path: str = Field(
        "data/sessions",
        env="CHAT_SESSION_STORE_PATH",
        description="Path to session storage directory",
    )

    startup_delay: int = Field(5, env="CHAT_STARTUP_DELAY")

    # MCP service URLs
    order_mcp_url: str = Field("http://order-service:8002/mcp", env="ORDER_MCP_URL")
    product_mcp_url: str = Field(
        "http://product-service:8003/mcp", env="PRODUCT_MCP_URL"
    )

    # Agent/LLM settings
    agent_model: str = Field("gpt-4o-mini", env="AGENT_MODEL")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")  # REQUIRED for chat!

    # Agent runtime settings
    tool_timeouts: int = Field(30, env="AGENT_TOOL_TIMEOUTS")
    tool_retries: int = Field(3, env="AGENT_TOOL_RETRIES")
    max_concurrent_tools: int = Field(5, env="AGENT_MAX_CONCURRENT_TOOLS")

    # CORS settings
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "https://*.onrender.com", "*"],
        env="CHAT_ALLOWED_ORIGINS",
    )

    # Prompt template settings
    system_prompt_template: str = Field(
        "system_prompt.j2", env="CHAT_SYSTEM_PROMPT_TEMPLATE"
    )

    # Feature flags
    include_strategies: bool = Field(False, env="CHAT_INCLUDE_STRATEGIES")
    debug: bool = Field(False, env="DEBUG")

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            # Handle JSON-like string from env var
            if v.startswith("["):
                import json

                return json.loads(v)
            # Handle comma-separated string
            return [origin.strip() for origin in v.split(",")]
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


# Singleton instance
config = ChatConfig()
