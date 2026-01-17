from __future__ import annotations
import sys

from pydantic import Field, PostgresDsn, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    database_url: PostgresDsn = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_newsletter"
    )

    # OpenAI configuration
    openai_api_key: str = Field(..., description="OpenAI API key (required)")

    # JWT configuration
    jwt_secret_key: str = Field(..., description="JWT secret key for token signing (required)")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30


def validate_settings() -> Settings:
    """Validate settings and provide helpful error messages for missing required fields."""
    try:
        return Settings()
    except ValidationError as e:
        missing_fields = []
        for error in e.errors():
            if error["type"] == "missing":
                field_name = error["loc"][0] if error["loc"] else "unknown"
                missing_fields.append(field_name.upper())

        if missing_fields:
            print("ERROR: Missing required environment variables:", file=sys.stderr)
            for field in missing_fields:
                print(f"  - {field}", file=sys.stderr)
            print(
                "\nPlease set these in your .env file (see env.example for reference)",
                file=sys.stderr,
            )
            sys.exit(1)

        # Re-raise if it's a different validation error
        raise


settings = validate_settings()
