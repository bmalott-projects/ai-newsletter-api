"""Unit tests for authentication utilities in app/core/auth.py.

These tests verify password hashing, JWT token creation, and token verification
without any external dependencies.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, status
from jose import jwt

from app.api.dependencies import get_current_user
from app.core.auth import (
    create_access_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.core.config import settings
from app.db.models.user import User


class TestPasswordHashing:
    """Test password hashing and verification functions."""

    def test_get_password_hash_returns_string(self) -> None:
        """Test that password hashing returns a string."""
        # Arrange
        password = "test_password_123"

        # Act
        hashed = get_password_hash(password)

        # Assert
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should be different from original

    def test_get_password_hash_different_for_same_password(self) -> None:
        """Test that hashing the same password multiple times produces different hashes."""
        # Arrange
        password = "test_password_123"

        # Act
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Assert
        assert hash1 != hash2

    def test_verify_password_correct(self) -> None:
        """Test that verify_password returns True for correct password."""
        # Arrange
        password = "test_password_123"
        hashed = get_password_hash(password)

        # Act
        result = verify_password(password, hashed)

        # Assert
        assert result is True

    def test_verify_password_incorrect(self) -> None:
        """Test that verify_password returns False for incorrect password."""
        # Arrange
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)

        # Act
        result = verify_password(wrong_password, hashed)

        # Assert
        assert result is False

    def test_verify_password_empty_password(self) -> None:
        """Test that verify_password handles empty password."""
        # Arrange
        password = "test_password_123"
        hashed = get_password_hash(password)

        # Act
        result = verify_password("", hashed)

        # Assert
        assert result is False

    def test_password_hash_handles_long_passwords(self) -> None:
        """Test that password hashing handles long passwords.

        Note: Currently bcrypt has a 72-byte limit. If the implementation
        pre-hashes with SHA256, this test would verify that functionality.
        """
        # Arrange
        long_password = "a" * 72

        # Act
        hashed = get_password_hash(long_password)
        result = verify_password(long_password, hashed)

        # Assert
        assert result is True

    def test_password_hash_rejects_too_long_passwords(self) -> None:
        """Test that password hashing rejects passwords longer than 72 bytes."""
        # Arrange
        too_long_password = "a" * 100

        # Act & Assert
        with pytest.raises(
            ValueError, match=r"Password must not exceed 72 bytes when UTF-8 encoded\."
        ):
            get_password_hash(too_long_password)


class TestJWTTokenCreation:
    """Test JWT token creation and verification."""

    def test_create_access_token_returns_string(self) -> None:
        """Test that create_access_token returns a string."""
        # Arrange
        data = {"sub": "123"}

        # Act
        token = create_access_token(data)

        # Assert
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expires_delta(self) -> None:
        """Test that create_access_token uses custom expiration time."""
        # Arrange
        data = {"sub": "123"}
        expires_delta = timedelta(minutes=30)

        # Act
        token = create_access_token(data, expires_delta=expires_delta)
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

        # Assert
        assert "exp" in payload
        assert "sub" in payload
        assert payload["sub"] == "123"
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        expected_time = datetime.now(UTC) + expires_delta
        assert abs((exp_time - expected_time).total_seconds()) < 5

    def test_create_access_token_with_default_expiration(self) -> None:
        """Test that create_access_token uses default expiration from settings."""
        # Arrange
        data = {"sub": "123"}

        # Act
        token = create_access_token(data)
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

        # Assert
        assert "exp" in payload
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        expected_time = datetime.now(UTC) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        assert abs((exp_time - expected_time).total_seconds()) < 5

    def test_create_access_token_preserves_data(self) -> None:
        """Test that create_access_token preserves all data in token."""
        # Arrange
        data = {"sub": "123", "custom_field": "custom_value", "role": "admin"}

        # Act
        token = create_access_token(data)
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

        # Assert
        assert payload["sub"] == "123"
        assert payload["custom_field"] == "custom_value"
        assert payload["role"] == "admin"


class TestJWTTokenVerification:
    """Test JWT token verification."""

    def test_verify_token_valid_token(self) -> None:
        """Test that verify_token returns payload for valid token."""
        # Arrange
        data = {"sub": "123", "custom": "value"}
        token = create_access_token(data)

        # Act
        payload = verify_token(token)

        # Assert
        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["custom"] == "value"
        assert "exp" in payload

    def test_verify_token_invalid_token(self) -> None:
        """Test that verify_token returns None for invalid token."""
        # Arrange
        invalid_token = "invalid.token.here"

        # Act
        payload = verify_token(invalid_token)

        # Assert
        assert payload is None

    def test_verify_token_wrong_secret(self) -> None:
        """Test that verify_token returns None for token with wrong secret."""
        # Arrange
        data = {"sub": "123"}
        wrong_secret_token = jwt.encode(data, "wrong_secret", algorithm=settings.jwt_algorithm)

        # Act
        payload = verify_token(wrong_secret_token)

        # Assert
        assert payload is None

    def test_verify_token_expired_token(self) -> None:
        """Test that verify_token returns None for expired token."""
        # Arrange
        expired_data = {"sub": "123", "exp": datetime.now(UTC) - timedelta(hours=1)}
        expired_token = jwt.encode(
            expired_data, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

        # Act
        payload = verify_token(expired_token)

        # Assert
        assert payload is None

    def test_verify_token_empty_string(self) -> None:
        """Test that verify_token handles empty string."""
        # Act
        payload = verify_token("")

        # Assert
        assert payload is None


class TestGetCurrentUser:
    """Test get_current_user FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self) -> None:
        """Test that get_current_user returns user for valid token."""
        # Arrange
        user_id = 123
        token = create_access_token(data={"sub": str(user_id)})
        mock_user = User(id=user_id, email="test@example.com", hashed_password="hashed")
        mock_auth = MagicMock()
        mock_auth.get_user_by_id = AsyncMock(return_value=mock_user)
        mock_uow = MagicMock()
        mock_uow.auth_service = mock_auth

        # Act
        result = await get_current_user(token=token, uow=mock_uow)

        # Assert
        assert result == mock_user
        assert result.id == user_id
        mock_auth.get_user_by_id.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self) -> None:
        """Test that get_current_user raises HTTPException for invalid token."""
        # Arrange
        invalid_token = "invalid.token"
        mock_uow = MagicMock()

        # Act
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=invalid_token, uow=mock_uow)

        # Assert
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        detail_payload = cast(dict[str, str], detail)
        assert detail_payload["error"] == "unauthorized"
        assert "credentials" in detail_payload["message"].lower()

    @pytest.mark.asyncio
    async def test_get_current_user_missing_sub(self) -> None:
        """Test that get_current_user raises HTTPException when token has no 'sub'."""
        # Arrange
        token = create_access_token(data={})
        mock_uow = MagicMock()

        # Act
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, uow=mock_uow)

        # Assert
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_user_id(self) -> None:
        """Test that get_current_user raises HTTPException for invalid user ID."""
        # Arrange
        token = create_access_token(data={"sub": "not_a_number"})
        mock_uow = MagicMock()

        # Act
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, uow=mock_uow)

        # Assert
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_nonexistent_user(self) -> None:
        """Test that get_current_user raises HTTPException when user doesn't exist."""
        # Arrange
        user_id = 999
        token = create_access_token(data={"sub": str(user_id)})
        mock_auth = MagicMock()
        mock_auth.get_user_by_id = AsyncMock(return_value=None)
        mock_uow = MagicMock()
        mock_uow.auth_service = mock_auth

        # Act
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, uow=mock_uow)

        # Assert
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
