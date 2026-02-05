"""Unit tests for configuration validation in app/core/config.py."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable, Iterator
from typing import cast

import pytest
from pydantic import ValidationError

from app.core import config
from app.core.config import Settings


@pytest.fixture
def test_settings_class() -> Iterator[Callable[[], Settings]]:
    """Fixture that provides the real Settings class without .env loading."""
    original_model_config = config.Settings.model_config
    config.Settings.model_config = {
        **original_model_config,
        "env_file": None,
    }
    try:
        yield cast(Callable[[], Settings], config.Settings)
    finally:
        config.Settings.model_config = original_model_config


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
    monkeypatch.setenv("JWT_SECRET_KEY", "StrongTestSecretKey123!@#AbcdXYZ")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("JWT_ALGORITHM", raising=False)


class TestSettingsValidation:
    """Test settings validation and error handling."""

    def test_settings_loads_successfully(
        self, test_settings_class: Callable[[], Settings], required_env_vars: None
    ) -> None:
        """Test that valid settings load correctly."""
        # Act
        settings = test_settings_class()

        # Assert
        assert settings.database_url is not None
        assert settings.openai_api_key == "test_key"
        assert settings.jwt_secret_key == "StrongTestSecretKey123!@#AbcdXYZ"
        assert settings.jwt_access_token_expire_minutes == 60

    def test_settings_missing_postgres_user(
        self,
        test_settings_class: Callable[[], Settings],
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing postgres_user raises ValidationError."""
        # Arrange
        monkeypatch.delenv("POSTGRES_USER", raising=False)

        # Act
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        # Assert
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("postgres_user",) for error in errors)

    def test_settings_missing_postgres_password(
        self,
        test_settings_class: Callable[[], Settings],
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing postgres_password raises ValidationError."""
        # Arrange
        monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

        # Act
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        # Assert
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("postgres_password",) for error in errors)

    def test_settings_missing_postgres_host(
        self,
        test_settings_class: Callable[[], Settings],
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing postgres_host raises ValidationError."""
        # Arrange
        monkeypatch.delenv("POSTGRES_HOST", raising=False)

        # Act
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        # Assert
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("postgres_host",) for error in errors)

    def test_settings_missing_postgres_port(
        self,
        test_settings_class: Callable[[], Settings],
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing postgres_port raises ValidationError."""
        # Arrange
        monkeypatch.delenv("POSTGRES_PORT", raising=False)

        # Act
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        # Assert
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("postgres_port",) for error in errors)

    def test_settings_missing_postgres_db(
        self,
        test_settings_class: Callable[[], Settings],
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing postgres_db raises ValidationError."""
        # Arrange
        monkeypatch.delenv("POSTGRES_DB", raising=False)

        # Act
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        # Assert
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("postgres_db",) for error in errors)

    def test_settings_missing_redis_host(
        self,
        test_settings_class: Callable[[], Settings],
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing redis_host raises ValidationError."""
        # Arrange
        monkeypatch.delenv("REDIS_HOST", raising=False)

        # Act
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        # Assert
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("redis_host",) for error in errors)

    def test_settings_missing_redis_port(
        self,
        test_settings_class: Callable[[], Settings],
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing redis_port raises ValidationError."""
        # Arrange
        monkeypatch.delenv("REDIS_PORT", raising=False)

        # Act
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        # Assert
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("redis_port",) for error in errors)

    def test_settings_missing_redis_db(
        self,
        test_settings_class: Callable[[], Settings],
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing redis_db raises ValidationError."""
        # Arrange
        monkeypatch.delenv("REDIS_DB", raising=False)

        # Act
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        # Assert
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("redis_db",) for error in errors)

    def test_settings_missing_jwt_secret_key(
        self,
        test_settings_class: Callable[[], Settings],
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing jwt_secret_key raises ValidationError."""
        # Arrange
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

        # Act
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        # Assert
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("jwt_secret_key",) for error in errors)

    @pytest.mark.parametrize(
        "weak_secret",
        [
            "too_Short123!",
            "lowercase32charswithnumberand1symbol!",
            "UPPERCASE32CHARSWITHNUMBERAND1SYMBOL!",
            "MixedCaseWithSymbolsButNoDigits!@#$",
            "MixedCaseWithDigits123ButNoSymbols",
        ],
    )
    def test_settings_rejects_weak_jwt_secret_variants(
        self,
        test_settings_class: Callable[[], Settings],
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
        weak_secret: str,
    ) -> None:
        """Test that weak JWT secrets are rejected by strength validator."""
        # Arrange
        monkeypatch.setenv("JWT_SECRET_KEY", weak_secret)

        # Act
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        # Assert
        errors = exc_info.value.errors()
        assert any(
            "JWT secret key must be at least 32 characters" in error.get("msg", "")
            for error in errors
        )

    def test_settings_missing_openai_api_key(
        self,
        test_settings_class: Callable[[], Settings],
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing openai_api_key raises ValidationError."""
        # Arrange
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Act
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        # Assert
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("openai_api_key",) for error in errors)

    def test_settings_missing_jwt_expire_minutes(
        self,
        test_settings_class: Callable[[], Settings],
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that missing jwt_access_token_expire_minutes raises ValidationError."""
        # Arrange
        monkeypatch.delenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)

        # Act
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        # Assert
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("jwt_access_token_expire_minutes",) for error in errors)

    def test_validate_settings_error_message(
        self,
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that validate_settings raises MissingRequiredSettingsError with helpful message."""
        # Arrange
        if "app.core.config" in sys.modules:
            importlib.reload(sys.modules["app.core.config"])

        from app.core import config

        original_model_config = config.Settings.model_config
        config.Settings.model_config = {
            **original_model_config,
            "env_file": None,
        }

        try:
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

            # Act
            with pytest.raises(config.MissingRequiredSettingsError) as exc_info:
                config.validate_settings()

            # Assert
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
        self, test_settings_class: Callable[[], Settings], required_env_vars: None
    ) -> None:
        """Test that optional fields work without env vars."""
        # Act
        settings = test_settings_class()

        # Assert
        assert settings.app_name == "ai-newsletter-api"
        assert settings.environment == "local"
        assert settings.log_level == "INFO"
        assert settings.jwt_algorithm == "HS256"

    def test_settings_invalid_database_url(
        self,
        test_settings_class: Callable[[], Settings],
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that invalid PostgresDsn format is rejected."""
        # Arrange
        monkeypatch.setenv("DATABASE_URL", "not-a-valid-url")

        # Act
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        # Assert
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("database_url",) for error in errors)

    def test_settings_environment_variable_override(
        self,
        test_settings_class: Callable[[], Settings],
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that environment variables override defaults."""
        # Arrange
        monkeypatch.setenv("APP_NAME", "custom-app-name")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("JWT_ALGORITHM", "RS256")

        # Act
        settings = test_settings_class()

        # Assert
        assert settings.app_name == "custom-app-name"
        assert settings.environment == "production"
        assert settings.log_level == "DEBUG"
        assert settings.jwt_algorithm == "RS256"

    def test_settings_jwt_expire_minutes_must_be_integer(
        self,
        test_settings_class: Callable[[], Settings],
        required_env_vars: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that jwt_access_token_expire_minutes must be a valid integer."""
        # Arrange
        monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "not-an-integer")

        # Act
        with pytest.raises(ValidationError) as exc_info:
            test_settings_class()

        # Assert
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("jwt_access_token_expire_minutes",) for error in errors)
