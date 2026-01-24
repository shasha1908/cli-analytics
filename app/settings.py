"""Application settings via environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration."""

    database_url: str = "postgresql://localhost:5432/cli_analytics"

    # Session timeout in minutes
    session_timeout_minutes: int = 30

    # Log level
    log_level: str = "INFO"

    # Privacy settings
    hash_salt: str = "cli-analytics-default-salt-change-in-production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
