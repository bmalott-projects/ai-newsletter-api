from __future__ import annotations

from pydantic import PostgresDsn
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
    openai_api_key: str

    # JWT configuration
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30


settings = Settings()
