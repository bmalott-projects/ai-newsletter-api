"""Unit tests for configuration validation in app/core/config.py."""

from __future__ import annotations

import importlib
import re
import sys
from typing import Any, Protocol, cast

import pytest
from pydantic import Field, PostgresDsn, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SettingsProtocol(Protocol):
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int
    postgres_db: str
    redis_host: str
    redis_port: int
    redis_db: int
    database_url: PostgresDsn
    rate_limit_storage_url: str
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
        postgres_user: str = Field(..., description="Postgres user (required)")
        postgres_password: str = Field(..., description="Postgres password (required)")
        postgres_host: str = Field(..., description="Postgres host (required)")
        postgres_port: int = Field(..., description="Postgres port (required)")
        postgres_db: str = Field(..., description="Postgres database name (required)")
        redis_host: str = Field(..., description="Redis host (required)")
        redis_port: int = Field(..., description="Redis port (required)")
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
        def build_derived_urls(self) -> TestSettings:
            if self.database_url is None:
                self.database_url = PostgresDsn.build(
                    scheme="postgresql+asyncpg",
                    username=self.postgres_user,
                    password=self.postgres_password,
                    host=self.postgres_host,
                    port=self.postgres_port,
                    path=self.postgres_db,
                )
            if self.rate_limit_storage_url is None:
                self.rate_limit_storage_url = (
                    f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
                )
            return self

        # Optional fields with defaults
        app_name: str = "ai-newsletter-api"
        environment: str = "local"
        log_level: str = "INFO"
        jwt_algorithm: str = "HS256"

        @staticmethod
        def _is_strong_jwt_secret(secret: str) -> bool:
            if len(secret) < 32:
                return False
            has_lower = re.search(r"[a-z]", secret) is not None
            has_upper = re.search(r"[A-Z]", secret) is not None
            has_digit = re.search(r"\d", secret) is not None
            has_symbol = re.search(r"[^\w\s]", secret) is not None
            return has_lower and has_upper and has_digit and has_symbol

        @model_validator(mode="after")
        def validate_jwt_secret_strength(self) -> TestSettings:
            if self.environment == "test":
                return self
            if not self._is_strong_jwt_secret(self.jwt_secret_key):
                raise ValueError(
                    "JWT secret key must be at least 32 characters and include upper, lower, "
                    "number, and symbol characters."
                )
            return self

    return cast(SettingsClass, TestSettings)


@pytest.fixture
def required_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture that sets all required environment variables for tests."""
    monkeypatch.setenv("POSTGRES_USER", "user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "db")
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_DB", "0")
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    monkeypatch.setenv("JWT_SECRET_KEY", "StrongSecretKeyWith123!@#AndMoreChars")
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
        assert settings.jwt_secret_key == "StrongSecretKeyWith123!@#AndMoreChars"
        assert settings.jwt_access_token_expire_minutes == 60

    def test_settings_missing_postgres_user(
        self,
        test_settings_class: SettingsClass,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing postgres_user raises ValidationError."""
        # Arrange: Set other required vars but not POSTGRES_USER
        monkeypatch.delenv("POSTGRES_USER", raising=False)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("postgres_user",) for error in errors)

    def test_settings_missing_postgres_password(
        self,
        test_settings_class: SettingsClass,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing postgres_password raises ValidationError."""
        # Arrange: Set other required vars but not POSTGRES_PASSWORD
        monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("postgres_password",) for error in errors)

    def test_settings_missing_postgres_host(
        self,
        test_settings_class: SettingsClass,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing postgres_host raises ValidationError."""
        # Arrange: Set other required vars but not POSTGRES_HOST
        monkeypatch.delenv("POSTGRES_HOST", raising=False)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("postgres_host",) for error in errors)

    def test_settings_missing_postgres_port(
        self,
        test_settings_class: SettingsClass,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing postgres_port raises ValidationError."""
        # Arrange: Set other required vars but not POSTGRES_PORT
        monkeypatch.delenv("POSTGRES_PORT", raising=False)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("postgres_port",) for error in errors)

    def test_settings_missing_postgres_db(
        self,
        test_settings_class: SettingsClass,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing postgres_db raises ValidationError."""
        # Arrange: Set other required vars but not POSTGRES_DB
        monkeypatch.delenv("POSTGRES_DB", raising=False)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("postgres_db",) for error in errors)

    def test_settings_missing_redis_host(
        self,
        test_settings_class: SettingsClass,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing redis_host raises ValidationError."""
        # Arrange: Set other required vars but not REDIS_HOST
        monkeypatch.delenv("REDIS_HOST", raising=False)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("redis_host",) for error in errors)

    def test_settings_missing_redis_port(
        self,
        test_settings_class: SettingsClass,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing redis_port raises ValidationError."""
        # Arrange: Set other required vars but not REDIS_PORT
        monkeypatch.delenv("REDIS_PORT", raising=False)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("redis_port",) for error in errors)

    def test_settings_missing_redis_db(
        self,
        test_settings_class: SettingsClass,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing redis_db raises ValidationError."""
        # Arrange: Set other required vars but not REDIS_DB
        monkeypatch.delenv("REDIS_DB", raising=False)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("redis_db",) for error in errors)

    def test_settings_missing_jwt_secret_key(
        self,
        test_settings_class: SettingsClass,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing jwt_secret_key raises ValidationError."""
        # Arrange: Set other required vars but not JWT_SECRET_KEY
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("jwt_secret_key",) for error in errors)

    def test_settings_rejects_weak_jwt_secret(
        self,
        test_settings_class: SettingsClass,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that weak JWT secrets are rejected."""
        monkeypatch.setenv("JWT_SECRET_KEY", "weak-secret")
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any("JWT secret key must be at least 32 characters" in str(err) for err in errors)

    def test_settings_allows_weak_jwt_secret_in_test_env(
        self,
        test_settings_class: SettingsClass,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that weak JWT secrets are allowed in test environment."""
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv("JWT_SECRET_KEY", "weak-secret")
        settings = test_settings_class()
        assert settings.jwt_secret_key == "weak-secret"

    def test_settings_missing_openai_api_key(
        self,
        test_settings_class: SettingsClass,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing openai_api_key raises ValidationError."""
        # Arrange: Set other required vars but not OPENAI_API_KEY
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("openai_api_key",) for error in errors)

    def test_settings_missing_jwt_expire_minutes(
        self,
        test_settings_class: SettingsClass,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing jwt_access_token_expire_minutes raises ValidationError."""
        # Arrange: Set other required vars but not JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        monkeypatch.delenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("jwt_access_token_expire_minutes",) for error in errors)

    def test_validate_settings_error_message(
        self,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that validate_settings raises MissingRequiredSettingsError with helpful message."""
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
            monkeypatch.delenv("POSTGRES_USER", raising=False)
            monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
            monkeypatch.delenv("POSTGRES_HOST", raising=False)
            monkeypatch.delenv("POSTGRES_PORT", raising=False)
            monkeypatch.delenv("POSTGRES_DB", raising=False)
            monkeypatch.delenv("REDIS_HOST", raising=False)
            monkeypatch.delenv("REDIS_PORT", raising=False)
            monkeypatch.delenv("REDIS_DB", raising=False)
            monkeypatch.delenv("OPENAI_API_KEY", raising=False)
            monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
            monkeypatch.delenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)

            # Act & Assert: Test the real validate_settings function
            with pytest.raises(config.MissingRequiredSettingsError) as exc_info:
                config.validate_settings()

            # Verify the exception contains missing fields
            missing_fields = exc_info.value.missing_fields
            assert len(missing_fields) > 0
            missing_fields_upper = {field.upper() for field in missing_fields}
            assert "POSTGRES_USER" in missing_fields_upper
            assert "POSTGRES_PASSWORD" in missing_fields_upper
            assert "POSTGRES_HOST" in missing_fields_upper
            assert "POSTGRES_PORT" in missing_fields_upper
            assert "POSTGRES_DB" in missing_fields_upper
            assert "REDIS_HOST" in missing_fields_upper
            assert "REDIS_PORT" in missing_fields_upper
            assert "REDIS_DB" in missing_fields_upper
            assert "OPENAI_API_KEY" in missing_fields_upper
            assert "JWT_SECRET_KEY" in missing_fields_upper
            assert "JWT_ACCESS_TOKEN_EXPIRE_MINUTES" in missing_fields_upper
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
        self,
        test_settings_class: SettingsClass,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that invalid PostgresDsn format is rejected."""
        # Arrange: Set invalid database URL
        monkeypatch.setenv("DATABASE_URL", "not-a-valid-url")

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        # Should have validation error for database_url override
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
        self,
        test_settings_class: SettingsClass,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that jwt_access_token_expire_minutes must be a valid integer."""
        # Arrange: Set invalid integer value
        monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "not-an-integer")

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("jwt_access_token_expire_minutes",) for error in errors)
