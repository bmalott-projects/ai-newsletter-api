"""Integration tests for API rate limiting."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from app.api.interests_api import get_llm_client
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
        statuses: list[int] = []
        for i in range(6):
            user_data = {"email": f"rate-limit-{i}@example.com", "password": "password123"}
            response = await async_http_client.post(
                "/api/auth/register",
                json=user_data,
            )
            statuses.append(response.status_code)

        assert statuses[:5] == [status.HTTP_201_CREATED] * 5
        assert statuses[5] == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.asyncio
    async def test_extract_rate_limited_by_token(
        self, async_http_client: AsyncClient, async_app: FastAPI
    ) -> None:
        """Test that extraction is rate-limited by token across IPs."""
        user_data = {"email": "limit-user@example.com", "password": "password123"}
        await async_http_client.post("/api/auth/register", json=user_data)
        login_response = await async_http_client.post("/api/auth/login", json=user_data)
        token = login_response.json()["access_token"]

        async_app.dependency_overrides[get_llm_client] = MockLLMClient

        statuses: list[int] = []
        for i in range(6):
            response = await async_http_client.post(
                "/api/interests/extract",
                json={"prompt": "Testing rate limits"},
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Forwarded-For": f"10.0.0.{i + 10}",
                },
            )
            statuses.append(response.status_code)

        assert statuses[:5] == [status.HTTP_200_OK] * 5
        assert statuses[5] == status.HTTP_429_TOO_MANY_REQUESTS

        second_user = {"email": "limit-user-2@example.com", "password": "password123"}
        await async_http_client.post("/api/auth/register", json=second_user)
        second_login = await async_http_client.post("/api/auth/login", json=second_user)
        second_token = second_login.json()["access_token"]

        second_response = await async_http_client.post(
            "/api/interests/extract",
            json={"prompt": "Testing rate limits"},
            headers={
                "Authorization": f"Bearer {second_token}",
                "X-Forwarded-For": "10.0.0.20",
            },
        )
        assert second_response.status_code == status.HTTP_200_OK

        async_app.dependency_overrides.pop(get_llm_client, None)
