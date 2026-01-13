"""
Configuration management for Governance OS.
Uses pydantic-settings for environment-based configuration.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_url: str = "postgresql://govos:local_dev_password@localhost:5432/governance_os"

    # API
    api_v1_prefix: str = "/api/v1"
    cors_origins: List[str] = ["http://localhost:3000"]

    # Logging
    log_level: str = "INFO"

    # Application
    app_name: str = "Governance OS"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
