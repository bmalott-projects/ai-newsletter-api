"""Integration tests for authentication API endpoints.

These tests verify the full HTTP request/response cycle, including:
- Request validation (Pydantic models)
- Authentication logic
- Database operations
- HTTP status codes and response formats
"""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    AccessTokenResponse,
    DeleteUserResponse,
    LoginUserRequest,
    RegisterUserRequest,
    UserResponse,
)
from app.db.models.user import User


class TestUserRegistration:
    """Test user registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_user_success(
        self, async_http_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test successful user registration."""
        # Arrange
        user_data = RegisterUserRequest(
            email="test@example.com",
            password="password123",
            confirm_password="password123",
        ).model_dump()

        # Act
        response = await async_http_client.post("/api/auth/register", json=user_data)

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        parsed = UserResponse.model_validate(response.json())
        assert parsed.email == "test@example.com"
        assert isinstance(parsed.id, int)

        async def verify_user_in_db(email: str, password: str) -> User:
            result = await db_session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            assert user is not None, f"User with email {email} not found in database"
            assert user.email == email
            assert user.hashed_password != password
            return user

        await verify_user_in_db(user_data["email"], user_data["password"])

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_http_client: AsyncClient) -> None:
        """Test that registering with an existing email returns 400."""
        # Arrange
        user_data = RegisterUserRequest(
            email="duplicate@example.com",
            password="password123",
            confirm_password="password123",
        ).model_dump()
        await async_http_client.post("/api/auth/register", json=user_data)

        # Act
        response = await async_http_client.post("/api/auth/register", json=user_data)

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        payload = response.json()
        assert payload["error"] == "user_exists"
        assert "already registered" in payload["message"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, async_http_client: AsyncClient) -> None:
        """Test that invalid email format is rejected."""
        # Arrange
        user_data = RegisterUserRequest.model_construct(
            email="not-an-email",
            password="password123",
            confirm_password="password123",
        ).model_dump()

        # Act
        response = await async_http_client.post("/api/auth/register", json=user_data)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_register_password_too_short(self, async_http_client: AsyncClient) -> None:
        """Test that password validation enforces minimum length."""
        # Arrange
        user_data = RegisterUserRequest.model_construct(
            email="test@example.com",
            password="short",
            confirm_password="short",
        ).model_dump()

        # Act
        response = await async_http_client.post("/api/auth/register", json=user_data)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        payload = response.json()
        assert payload["error"] == "validation_error"
        assert payload["message"] == "Request validation failed"
        error_detail = payload["details"]
        assert any("password" in str(err).lower() for err in error_detail)


class TestUserLogin:
    """Test user login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, async_http_client: AsyncClient) -> None:
        """Test successful login returns JWT token."""
        # Arrange
        register_payload = RegisterUserRequest(
            email="login@example.com",
            password="password123",
            confirm_password="password123",
        ).model_dump()
        await async_http_client.post("/api/auth/register", json=register_payload)

        login_payload = LoginUserRequest(
            email="login@example.com", password="password123"
        ).model_dump()

        # Act
        response = await async_http_client.post("/api/auth/login", json=login_payload)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        parsed = AccessTokenResponse.model_validate(response.json())
        assert parsed.token_type == "bearer"
        assert len(parsed.access_token) > 0

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_http_client: AsyncClient) -> None:
        """Test that wrong password returns 401."""
        # Arrange
        register_payload = RegisterUserRequest(
            email="wrongpass@example.com",
            password="password123",
            confirm_password="password123",
        ).model_dump()
        await async_http_client.post("/api/auth/register", json=register_payload)

        # Act
        login_payload = LoginUserRequest(
            email="wrongpass@example.com", password="wrongpassword"
        ).model_dump()
        response = await async_http_client.post("/api/auth/login", json=login_payload)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        payload = response.json()
        assert payload["error"] == "invalid_credentials"
        assert "incorrect" in payload["message"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_http_client: AsyncClient) -> None:
        """Test that login with non-existent user returns 401."""
        # Arrange
        login_payload = LoginUserRequest(
            email="nonexistent@example.com", password="password123"
        ).model_dump()

        # Act
        response = await async_http_client.post("/api/auth/login", json=login_payload)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestProtectedEndpoints:
    """Test endpoints that require authentication."""

    @pytest.mark.asyncio
    async def test_get_me_without_token(self, async_http_client: AsyncClient) -> None:
        """Test that accessing protected endpoint without token returns 401."""
        # Act
        response = await async_http_client.get("/api/auth/me")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_me_with_valid_token(self, async_http_client: AsyncClient) -> None:
        """Test that accessing /me with valid token returns user info."""
        # Arrange
        user_data = RegisterUserRequest(
            email="me@example.com",
            password="password123",
            confirm_password="password123",
        ).model_dump()
        await async_http_client.post("/api/auth/register", json=user_data)
        login_payload = LoginUserRequest(
            email="me@example.com", password="password123"
        ).model_dump()
        login_response = await async_http_client.post("/api/auth/login", json=login_payload)
        token = AccessTokenResponse.model_validate(login_response.json()).access_token

        # Act
        response = await async_http_client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        parsed = UserResponse.model_validate(response.json())
        assert parsed.email == "me@example.com"
        assert isinstance(parsed.id, int)

    @pytest.mark.asyncio
    async def test_get_me_with_invalid_token(self, async_http_client: AsyncClient) -> None:
        """Test that invalid token returns 401."""
        # Act
        response = await async_http_client.get(
            "/api/auth/me", headers={"Authorization": "Bearer invalid_token_here"}
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_delete_me_success(
        self, async_http_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that user can delete their own account."""
        # Arrange
        user_data = RegisterUserRequest(
            email="delete@example.com",
            password="password123",
            confirm_password="password123",
        ).model_dump()
        await async_http_client.post("/api/auth/register", json=user_data)
        login_payload = LoginUserRequest(
            email="delete@example.com", password="password123"
        ).model_dump()
        login_response = await async_http_client.post("/api/auth/login", json=login_payload)
        token = AccessTokenResponse.model_validate(login_response.json()).access_token

        # Act
        response = await async_http_client.delete(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        parsed = DeleteUserResponse.model_validate(response.json())
        assert parsed.deleted_user_id is not None

        async def verify_user_deleted(email: str) -> None:
            result = await db_session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            assert user is None, f"User with email {email} still exists in database"

        await verify_user_deleted("delete@example.com")
