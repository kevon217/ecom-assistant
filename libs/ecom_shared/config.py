"""Shared configuration base classes only."""

from pydantic import Field
from pydantic_settings import BaseSettings


class BaseServiceConfig(BaseSettings):
    """Base configuration class for services to extend."""

    port: int = Field(8000, env="PORT")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    model_config = {"env_file": ".env", "case_sensitive": False}
