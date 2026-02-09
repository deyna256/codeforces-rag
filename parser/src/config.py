"""Configuration module for codeforces-editorial-finder."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # HTTP
    http_retries: int = Field(default=3, description="Number of HTTP retry attempts")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # LLM (OpenRouter)
    openrouter_api_key: str = Field(
        description="OpenRouter API key for LLM-based editorial detection"
    )
    openrouter_model: str = Field(
        default="anthropic/claude-3.5-haiku",
        description="OpenRouter model to use for editorial detection",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL",
    )

    @field_validator("openrouter_api_key")
    @classmethod
    def validate_openrouter_api_key(cls, v: str) -> str:
        if not v.startswith("sk-or-"):
            raise ValueError("OPENROUTER_API_KEY must start with 'sk-or-'")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper


# Singleton instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create settings singleton instance."""
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[missing-argument]  # loaded from env
    return _settings
