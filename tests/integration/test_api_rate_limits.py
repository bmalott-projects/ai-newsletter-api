"""Integration tests for API rate limiting."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from app.api.interests_api import get_llm_client
from app.api.schemas import (
    InterestExtractionRequest,
    LoginResponse,
    LoginUserRequest,
    RegisterUserRequest,
    UserResponse,
)
from app.llm.client import LLMClient
from app.llm.schemas import InterestExtractionResult


class MockLLMClient(LLMClient):
    """Mock LLM client for rate limit tests."""

    async def extract_interests(self, prompt: str) -> InterestExtractionResult:
        return InterestExtractionResult()


class TestRateLimits:
    """Test API rate limit behavior."""

    @pytest.mark.asyncio
    async def test_register_rate_limited(self, async_http_client: AsyncClient) -> None:
        """Test that registration is rate-limited."""
        # Arrange
        statuses: list[int] = []
        for i in range(6):
            payload = RegisterUserRequest(
                email=f"rate-limit-{i}@example.com", password="password123"
            ).model_dump()
            # Act
            response = await async_http_client.post(
                "/api/auth/register",
                json=payload,
            )
            statuses.append(response.status_code)
            if response.status_code == status.HTTP_201_CREATED:
                UserResponse.model_validate(response.json())
        # Assert
        assert statuses[:5] == [status.HTTP_201_CREATED] * 5
        assert statuses[5] == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.asyncio
    async def test_extract_rate_limited_by_token(
        self, async_http_client: AsyncClient, async_app: FastAPI
    ) -> None:
        """Test that extraction is rate-limited by token across IPs."""
        # Arrange
        register_payload = RegisterUserRequest(
            email="limit-user@example.com", password="password123"
        ).model_dump()
        await async_http_client.post("/api/auth/register", json=register_payload)
        login_payload = LoginUserRequest(
            email="limit-user@example.com", password="password123"
        ).model_dump()
        login_response = await async_http_client.post("/api/auth/login", json=login_payload)
        token = LoginResponse.model_validate(login_response.json()).access_token

        async_app.dependency_overrides[get_llm_client] = lambda: MockLLMClient()

        extract_payload = InterestExtractionRequest(prompt="Testing rate limits").model_dump()
        statuses: list[int] = []
        for i in range(6):
            # Act
            response = await async_http_client.post(
                "/api/interests/extract",
                json=extract_payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Forwarded-For": f"10.0.0.{i + 10}",
                },
            )
            statuses.append(response.status_code)
            if response.status_code == status.HTTP_200_OK:
                InterestExtractionResult.model_validate(response.json())
        # Assert
        assert statuses[:5] == [status.HTTP_200_OK] * 5
        assert statuses[5] == status.HTTP_429_TOO_MANY_REQUESTS

        second_register = RegisterUserRequest(
            email="limit-user-2@example.com", password="password123"
        ).model_dump()
        await async_http_client.post("/api/auth/register", json=second_register)
        second_login_payload = LoginUserRequest(
            email="limit-user-2@example.com", password="password123"
        ).model_dump()
        second_login = await async_http_client.post("/api/auth/login", json=second_login_payload)
        second_token = LoginResponse.model_validate(second_login.json()).access_token

        # Act
        second_response = await async_http_client.post(
            "/api/interests/extract",
            json=extract_payload,
            headers={
                "Authorization": f"Bearer {second_token}",
                "X-Forwarded-For": "10.0.0.20",
            },
        )
        # Assert
        assert second_response.status_code == status.HTTP_200_OK
        InterestExtractionResult.model_validate(second_response.json())

        async_app.dependency_overrides.pop(get_llm_client, None)
