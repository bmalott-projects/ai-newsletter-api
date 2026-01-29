from __future__ import annotations

from pydantic import Field, PostgresDsn, ValidationError, model_validator
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

    # Required environment variables
    api_port: int = Field(..., description="API port (required)")
    postgres_user: str = Field(..., description="Postgres user (required)")
    postgres_password: str = Field(..., description="Postgres password (required)")
    postgres_host: str = Field(..., description="Postgres host (required)")
    postgres_db: str = Field(..., description="Postgres database name (required)")
    redis_host: str = Field(..., description="Redis host (required)")
    redis_db: int = Field(..., description="Redis database number (required)")
    openai_api_key: str = Field(..., description="OpenAI API key (required)")
    jwt_secret_key: str = Field(..., description="JWT secret key for token signing (required)")
    jwt_access_token_expire_minutes: int = Field(
        ..., description="JWT token expiration in minutes (required)"
    )

    # Database/Redis urls built from components
    database_url: PostgresDsn | None = Field(
        default=None,
        description="Database connection URL",
    )
    rate_limit_storage_url: str | None = Field(
        default=None,
        description="Rate limit storage URL",
    )

    @model_validator(mode="after")
    def build_derived_urls(self) -> Settings:
        """Build URLs from components when missing."""
        if self.database_url is None:
            self.database_url = PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                path=self.postgres_db,
            )
        if self.rate_limit_storage_url is None:
            self.rate_limit_storage_url = f"redis://{self.redis_host}:6379/{self.redis_db}"
        return self

    # Optional environment variables (defaults provided)
    app_name: str = "ai-newsletter-api"
    environment: str = "local"
    log_level: str = "INFO"
    jwt_algorithm: str = "HS256"


def validate_settings() -> Settings:
    """Validate settings and raise exception for missing required fields.

    Raises:
        MissingRequiredSettingsError: If required environment variables are missing
        ValidationError: For other validation errors
    """
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as e:
        missing_fields: list[str] = []
        for error in e.errors():
            if error["type"] == "missing":
                field_name = error["loc"][0] if error["loc"] else "unknown"
                if isinstance(field_name, str):
                    missing_fields.append(field_name.upper())
                else:
                    missing_fields.append(str(field_name).upper())

        if missing_fields:
            raise MissingRequiredSettingsError(missing_fields) from e

        # Re-raise if it's a different validation error
        raise


# Validate settings at import time.
# Exceptions will propagate to the importing module (e.g., app/main.py)
settings = validate_settings()
