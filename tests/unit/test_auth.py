"""Unit tests for authentication utilities in app/core/auth.py.

These tests verify password hashing, JWT token creation, and token verification
without any external dependencies.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jose import jwt

from app.core.auth import (
    create_access_token,
    get_current_user,
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
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should be different from original

    def test_get_password_hash_different_for_same_password(self) -> None:
        """Test that hashing the same password multiple times produces different hashes."""
        password = "test_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Bcrypt includes salt, so hashes should be different
        assert hash1 != hash2

    def test_verify_password_correct(self) -> None:
        """Test that verify_password returns True for correct password."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self) -> None:
        """Test that verify_password returns False for incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_password(self) -> None:
        """Test that verify_password handles empty password."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password("", hashed) is False

    def test_password_hash_handles_long_passwords(self) -> None:
        """Test that password hashing handles long passwords.

        Note: Currently bcrypt has a 72-byte limit. If the implementation
        pre-hashes with SHA256, this test would verify that functionality.
        """
        # Create a password at the bcrypt limit (72 bytes)
        long_password = "a" * 72
        hashed = get_password_hash(long_password)

        # Should be able to verify
        assert verify_password(long_password, hashed) is True

    def test_password_hash_rejects_too_long_passwords(self) -> None:
        """Test that password hashing rejects passwords longer than 72 bytes."""
        # Create a password longer than 72 bytes (bcrypt limit)
        too_long_password = "a" * 100

        # Should raise ValueError
        with pytest.raises(ValueError, match="password cannot be longer than 72 bytes"):
            get_password_hash(too_long_password)


class TestJWTTokenCreation:
    """Test JWT token creation and verification."""

    def test_create_access_token_returns_string(self) -> None:
        """Test that create_access_token returns a string."""
        data = {"sub": "123"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expires_delta(self) -> None:
        """Test that create_access_token uses custom expiration time."""
        data = {"sub": "123"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=expires_delta)

        # Decode and verify expiration
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert "exp" in payload
        assert "sub" in payload
        assert payload["sub"] == "123"

        # Check expiration is approximately 30 minutes from now
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        expected_time = datetime.now(UTC) + expires_delta
        # Allow 5 second tolerance
        assert abs((exp_time - expected_time).total_seconds()) < 5

    def test_create_access_token_with_default_expiration(self) -> None:
        """Test that create_access_token uses default expiration from settings."""
        data = {"sub": "123"}
        token = create_access_token(data)

        # Decode and verify expiration
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert "exp" in payload

        # Check expiration is approximately the default time from now
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        expected_time = datetime.now(UTC) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        # Allow 5 second tolerance
        assert abs((exp_time - expected_time).total_seconds()) < 5

    def test_create_access_token_preserves_data(self) -> None:
        """Test that create_access_token preserves all data in token."""
        data = {"sub": "123", "custom_field": "custom_value", "role": "admin"}
        token = create_access_token(data)

        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == "123"
        assert payload["custom_field"] == "custom_value"
        assert payload["role"] == "admin"


class TestJWTTokenVerification:
    """Test JWT token verification."""

    def test_verify_token_valid_token(self) -> None:
        """Test that verify_token returns payload for valid token."""
        data = {"sub": "123", "custom": "value"}
        token = create_access_token(data)

        payload = verify_token(token)

        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["custom"] == "value"
        assert "exp" in payload

    def test_verify_token_invalid_token(self) -> None:
        """Test that verify_token returns None for invalid token."""
        invalid_token = "invalid.token.here"

        payload = verify_token(invalid_token)

        assert payload is None

    def test_verify_token_wrong_secret(self) -> None:
        """Test that verify_token returns None for token with wrong secret."""
        data = {"sub": "123"}
        # Create token with wrong secret
        wrong_secret_token = jwt.encode(data, "wrong_secret", algorithm=settings.jwt_algorithm)

        payload = verify_token(wrong_secret_token)

        assert payload is None

    def test_verify_token_expired_token(self) -> None:
        """Test that verify_token returns None for expired token."""
        # Create expired token
        expired_data = {"sub": "123", "exp": datetime.now(UTC) - timedelta(hours=1)}
        expired_token = jwt.encode(
            expired_data, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

        payload = verify_token(expired_token)

        assert payload is None

    def test_verify_token_empty_string(self) -> None:
        """Test that verify_token handles empty string."""
        payload = verify_token("")

        assert payload is None


class TestGetCurrentUser:
    """Test get_current_user FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self) -> None:
        """Test that get_current_user returns user for valid token."""
        # Arrange
        user_id = 123
        token = create_access_token(data={"sub": str(user_id)})

        # Mock database session
        mock_user = User(id=user_id, email="test@example.com", hashed_password="hashed")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock oauth2_scheme dependency
        with patch("app.core.auth.oauth2_scheme") as mock_scheme:
            mock_scheme.return_value = token

            # Act
            result = await get_current_user(token=token, db=mock_db)

            # Assert
            assert result == mock_user
            assert result.id == user_id
            mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self) -> None:
        """Test that get_current_user raises HTTPException for invalid token."""
        # Arrange
        invalid_token = "invalid.token"

        # Mock database session
        mock_db = AsyncMock()

        # Act & Assert
        from fastapi import HTTPException, status

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=invalid_token, db=mock_db)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "credentials" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_current_user_missing_sub(self) -> None:
        """Test that get_current_user raises HTTPException when token has no 'sub'."""
        # Arrange
        token = create_access_token(data={})  # No 'sub' field

        # Mock database session
        mock_db = AsyncMock()

        # Act & Assert
        from fastapi import HTTPException, status

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=mock_db)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_user_id(self) -> None:
        """Test that get_current_user raises HTTPException for invalid user ID."""
        # Arrange
        token = create_access_token(data={"sub": "not_a_number"})

        # Mock database session
        mock_db = AsyncMock()

        # Act & Assert
        from fastapi import HTTPException, status

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=mock_db)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_nonexistent_user(self) -> None:
        """Test that get_current_user raises HTTPException when user doesn't exist."""
        # Arrange
        user_id = 999
        token = create_access_token(data={"sub": str(user_id)})

        # Mock database session - return None (user not found)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act & Assert
        from fastapi import HTTPException, status

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=mock_db)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
