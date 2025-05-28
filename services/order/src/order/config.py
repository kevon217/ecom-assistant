"""Order service configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings


class OrderConfig(BaseSettings):
    """Order service specific configuration."""

    # Service settings
    port: int = Field(8002, env="PORT")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # Data settings - absolute path for Docker, relative for local
    data_path: str = Field(
        "data/orders_cleaned.csv",
        env="ORDER_DATA_PATH",
        description="Path to orders CSV file",
    )

    # Optional OpenAI key (not used by order service)
    openai_api_key: str | None = Field(None, env="OPENAI_API_KEY")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


# Singleton instance
config = OrderConfig()
