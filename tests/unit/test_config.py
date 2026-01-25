"""Unit tests for configuration validation in app/core/config.py."""

from __future__ import annotations

import importlib
import sys
from typing import Any, Protocol, cast

import pytest
from pydantic import Field, PostgresDsn, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class SettingsProtocol(Protocol):
    database_url: PostgresDsn
    openai_api_key: str
    jwt_secret_key: str
    jwt_access_token_expire_minutes: int
    app_name: str
    environment: str
    log_level: str
    jwt_algorithm: str


class SettingsClass(Protocol):
    def __call__(self, **kwargs: Any) -> SettingsProtocol: ...


@pytest.fixture
def test_settings_class() -> SettingsClass:
    """Fixture that provides a TestSettings class without .env file loading."""

    class TestSettings(BaseSettings):
        model_config = SettingsConfigDict(env_file=None, extra="ignore")
        database_url: PostgresDsn = Field(..., description="Database connection URL (required)")
        openai_api_key: str = Field(..., description="OpenAI API key (required)")
        jwt_secret_key: str = Field(..., description="JWT secret key for token signing (required)")
        jwt_access_token_expire_minutes: int = Field(
            ..., description="JWT token expiration in minutes (required)"
        )
        # Optional fields with defaults
        app_name: str = "ai-newsletter-api"
        environment: str = "local"
        log_level: str = "INFO"
        jwt_algorithm: str = "HS256"

    return cast(SettingsClass, TestSettings)


@pytest.fixture
def required_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture that sets all required environment variables for tests."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    monkeypatch.setenv("JWT_SECRET_KEY", "test_secret")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("JWT_ALGORITHM", raising=False)


class TestSettingsValidation:
    """Test settings validation and error handling."""

    def test_settings_loads_successfully(
        self, test_settings_class: SettingsClass, required_env_vars: None
    ) -> None:
        """Test that valid settings load correctly."""
        # Act
        settings = test_settings_class()

        # Assert
        assert settings.database_url is not None
        assert settings.openai_api_key == "test_key"
        assert settings.jwt_secret_key == "test_secret"
        assert settings.jwt_access_token_expire_minutes == 60

    def test_settings_missing_database_url(
        self, test_settings_class: SettingsClass, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing database_url raises ValidationError."""
        # Arrange: Set other required vars but not DATABASE_URL
        monkeypatch.setenv("OPENAI_API_KEY", "test_key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test_secret")
        monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        monkeypatch.delenv("DATABASE_URL", raising=False)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("database_url",) for error in errors)

    def test_settings_missing_jwt_secret_key(
        self, test_settings_class: SettingsClass, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing jwt_secret_key raises ValidationError."""
        # Arrange: Set other required vars but not JWT_SECRET_KEY
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
        monkeypatch.setenv("OPENAI_API_KEY", "test_key")
        monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("jwt_secret_key",) for error in errors)

    def test_settings_missing_openai_api_key(
        self, test_settings_class: SettingsClass, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing openai_api_key raises ValidationError."""
        # Arrange: Set other required vars but not OPENAI_API_KEY
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
        monkeypatch.setenv("JWT_SECRET_KEY", "test_secret")
        monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("openai_api_key",) for error in errors)

    def test_settings_missing_jwt_expire_minutes(
        self, test_settings_class: SettingsClass, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing jwt_access_token_expire_minutes raises ValidationError."""
        # Arrange: Set other required vars but not JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
        monkeypatch.setenv("OPENAI_API_KEY", "test_key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test_secret")
        monkeypatch.delenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("jwt_access_token_expire_minutes",) for error in errors)

    def test_validate_settings_error_message(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that validate_settings raises MissingRequiredSettingsError with helpful message."""
        # Arrange: Set required env vars so module import succeeds
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
        monkeypatch.setenv("OPENAI_API_KEY", "test_key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test_secret")
        monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")

        # Reload the config module to get a fresh validate_settings function
        if "app.core.config" in sys.modules:
            importlib.reload(sys.modules["app.core.config"])

        # Need to import after the reload (inline, not at the top of the file)
        from app.core import config

        # Prevent Settings from reading .env file by patching model_config
        original_model_config = config.Settings.model_config
        config.Settings.model_config = {
            **original_model_config,
            "env_file": None,  # Disable .env file loading
        }

        try:
            # Remove required env vars to trigger the error
            monkeypatch.delenv("DATABASE_URL", raising=False)
            monkeypatch.delenv("OPENAI_API_KEY", raising=False)
            monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
            monkeypatch.delenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)

            # Act & Assert: Test the real validate_settings function
            with pytest.raises(config.MissingRequiredSettingsError) as exc_info:
                config.validate_settings()

            # Verify the exception contains missing fields
            missing_fields = exc_info.value.missing_fields
            assert len(missing_fields) > 0
            assert "DATABASE_URL" in missing_fields or "database_url".upper() in [
                f.upper() for f in missing_fields
            ]
            assert "Missing required environment variables" in str(exc_info.value)
        finally:
            # Restore original model_config
            config.Settings.model_config = original_model_config

    def test_settings_optional_fields_have_defaults(
        self, test_settings_class: SettingsClass, required_env_vars: None
    ) -> None:
        """Test that optional fields work without env vars."""
        # Act
        settings = test_settings_class()

        # Assert: Optional fields have defaults
        assert settings.app_name == "ai-newsletter-api"
        assert settings.environment == "local"
        assert settings.log_level == "INFO"
        assert settings.jwt_algorithm == "HS256"

    def test_settings_invalid_database_url(
        self, test_settings_class: SettingsClass, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that invalid PostgresDsn format is rejected."""
        # Arrange: Set invalid database URL
        monkeypatch.setenv("DATABASE_URL", "not-a-valid-url")
        monkeypatch.setenv("OPENAI_API_KEY", "test_key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test_secret")
        monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        # Should have validation error for database_url
        assert any(error["loc"] == ("database_url",) for error in errors)

    def test_settings_environment_variable_override(
        self,
        test_settings_class: SettingsClass,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that environment variables override defaults."""
        # Arrange: Set optional overrides
        monkeypatch.setenv("APP_NAME", "custom-app-name")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("JWT_ALGORITHM", "RS256")

        # Act
        settings = test_settings_class()

        # Assert: Environment variables override defaults
        assert settings.app_name == "custom-app-name"
        assert settings.environment == "production"
        assert settings.log_level == "DEBUG"
        assert settings.jwt_algorithm == "RS256"

    def test_settings_jwt_expire_minutes_must_be_integer(
        self, test_settings_class: SettingsClass, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that jwt_access_token_expire_minutes must be a valid integer."""
        # Arrange: Set invalid integer value
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
        monkeypatch.setenv("OPENAI_API_KEY", "test_key")
        monkeypatch.setenv("JWT_SECRET_KEY", "test_secret")
        monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "not-an-integer")

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("jwt_access_token_expire_minutes",) for error in errors)
