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

from app.db.models.user import User


class TestUserRegistration:
    """Test user registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_user_success(
        self, async_http_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test successful user registration."""
        # Arrange: Prepare request data
        user_data = {"email": "test@example.com", "password": "password123"}

        # Act: Make HTTP request
        response = await async_http_client.post("/api/auth/register", json=user_data)

        # Assert: Check response
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["email"] == "test@example.com"
        assert "id" in response_data
        assert isinstance(response_data["id"], int)

        async def verify_user_in_db(email: str, password: str) -> User:
            result = await db_session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            assert user is not None, f"User with email {email} not found in database"
            assert user.email == email
            assert user.hashed_password != password
            return user

        # Assert: Verify user was created in database
        await verify_user_in_db(user_data["email"], user_data["password"])

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_http_client: AsyncClient) -> None:
        """Test that registering with an existing email returns 400."""
        # Arrange: Register first user
        user_data = {"email": "duplicate@example.com", "password": "password123"}
        await async_http_client.post("/api/auth/register", json=user_data)

        # Act: Try to register again with same email
        response = await async_http_client.post("/api/auth/register", json=user_data)

        # Assert: Should return 400 Bad Request
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, async_http_client: AsyncClient) -> None:
        """Test that invalid email format is rejected."""
        # Arrange: Invalid email
        user_data = {"email": "not-an-email", "password": "password123"}

        # Act
        response = await async_http_client.post("/api/auth/register", json=user_data)

        # Assert: Should return 422 Validation Error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_register_password_too_short(self, async_http_client: AsyncClient) -> None:
        """Test that password validation enforces minimum length."""
        # Arrange: Password too short
        user_data = {"email": "test@example.com", "password": "short"}  # Less than 8 characters

        # Act
        response = await async_http_client.post("/api/auth/register", json=user_data)

        # Assert: Should return 422 Validation Error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        error_detail = response.json()["detail"]
        # Check that the error mentions password length
        assert any("password" in str(err).lower() for err in error_detail)


class TestUserLogin:
    """Test user login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, async_http_client: AsyncClient) -> None:
        """Test successful login returns JWT token."""
        # Arrange: Register a user first
        user_data = {"email": "login@example.com", "password": "password123"}
        await async_http_client.post("/api/auth/register", json=user_data)

        # Act: Login with correct credentials
        response = await async_http_client.post("/api/auth/login", json=user_data)

        # Assert: Should return 200 with token
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert "access_token" in response_data
        assert response_data["token_type"] == "bearer"
        assert len(response_data["access_token"]) > 0

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_http_client: AsyncClient) -> None:
        """Test that wrong password returns 401."""
        # Arrange: Register a user
        user_data = {"email": "wrongpass@example.com", "password": "password123"}
        await async_http_client.post("/api/auth/register", json=user_data)

        # Act: Try to login with wrong password
        response = await async_http_client.post(
            "/api/auth/login", json={"email": "wrongpass@example.com", "password": "wrongpassword"}
        )

        # Assert: Should return 401 Unauthorized
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_http_client: AsyncClient) -> None:
        """Test that login with non-existent user returns 401."""
        # Act: Try to login with user that doesn't exist
        response = await async_http_client.post(
            "/api/auth/login", json={"email": "nonexistent@example.com", "password": "password123"}
        )

        # Assert: Should return 401 Unauthorized
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestProtectedEndpoints:
    """Test endpoints that require authentication."""

    @pytest.mark.asyncio
    async def test_get_me_without_token(self, async_http_client: AsyncClient) -> None:
        """Test that accessing protected endpoint without token returns 401."""
        # Act: Try to access /me without authentication
        response = await async_http_client.get("/api/auth/me")

        # Assert: Should return 401 Unauthorized
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_me_with_valid_token(self, async_http_client: AsyncClient) -> None:
        """Test that accessing /me with valid token returns user info."""
        # Arrange: Register and login to get token
        user_data = {"email": "me@example.com", "password": "password123"}
        await async_http_client.post("/api/auth/register", json=user_data)
        login_response = await async_http_client.post("/api/auth/login", json=user_data)
        token = login_response.json()["access_token"]

        # Act: Access protected endpoint with token
        response = await async_http_client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        # Assert: Should return 200 with user info
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["email"] == "me@example.com"
        assert "id" in response_data

    @pytest.mark.asyncio
    async def test_get_me_with_invalid_token(self, async_http_client: AsyncClient) -> None:
        """Test that invalid token returns 401."""
        # Act: Try to access with fake token
        response = await async_http_client.get(
            "/api/auth/me", headers={"Authorization": "Bearer invalid_token_here"}
        )

        # Assert: Should return 401 Unauthorized
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_delete_me_success(
        self, async_http_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that user can delete their own account."""
        # Arrange: Register and login
        user_data = {"email": "delete@example.com", "password": "password123"}
        await async_http_client.post("/api/auth/register", json=user_data)
        login_response = await async_http_client.post("/api/auth/login", json=user_data)
        token = login_response.json()["access_token"]

        # Act: Delete account
        response = await async_http_client.delete(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        # Assert: Should return 200 OK with deleted user ID
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["deleted_user_id"] is not None

        async def verify_user_deleted(email: str) -> None:
            result = await db_session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            assert user is None, f"User with email {email} still exists in database"

        # Assert: Verify user was deleted from database
        await verify_user_deleted("delete@example.com")
