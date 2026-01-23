from __future__ import annotations

from pydantic import Field, PostgresDsn, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class MissingRequiredSettingsError(Exception):
    """Raised when required settings are missing."""

    def __init__(self, missing_fields: list[str]) -> None:
        """Initialize with list of missing field names."""
        self.missing_fields = missing_fields
        super().__init__(f"Missing required environment variables: {', '.join(missing_fields)}")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Fallback values if there is no .env file
    app_name: str = "ai-newsletter-api"
    environment: str = "local"
    log_level: str = "INFO"

    # Database configuration (required to prevent accidental connection to wrong database)
    database_url: PostgresDsn = Field(..., description="Database connection URL (required)")

    # OpenAI configuration
    openai_api_key: str = Field(..., description="OpenAI API key (required)")

    # JWT configuration
    jwt_secret_key: str = Field(..., description="JWT secret key for token signing (required)")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(
        ..., description="JWT token expiration in minutes (required)"
    )


def validate_settings() -> Settings:
    """Validate settings and raise exception for missing required fields.

    Raises:
        MissingRequiredSettingsError: If required environment variables are missing
        ValidationError: For other validation errors
    """
    try:
        return Settings()
    except ValidationError as e:
        missing_fields = []
        for error in e.errors():
            if error["type"] == "missing":
                field_name = error["loc"][0] if error["loc"] else "unknown"
                missing_fields.append(field_name.upper())

        if missing_fields:
            raise MissingRequiredSettingsError(missing_fields) from e

        # Re-raise if it's a different validation error
        raise


# Validate settings at import time.
# Exceptions will propagate to the importing module (e.g., app/main.py)
settings = validate_settings()
