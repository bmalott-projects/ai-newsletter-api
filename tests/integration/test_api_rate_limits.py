"""Integration tests for API rate limiting."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable

import pytest
from fastapi import FastAPI, Request, status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import UnitOfWork, get_uow
from app.api.schemas import (
    AccessTokenResponse,
    InterestExtractionRequest,
    InterestExtractionResponse,
    LoginUserRequest,
    RegisterUserRequest,
    UserResponse,
)
from app.db.session import get_session_maker
from app.llm.client import LLMClient
from app.llm.schemas import InterestExtractionResult
from app.services.interest_service import InterestService


class MockLLMClient(LLMClient):
    """Mock LLM client for rate limit tests."""

    async def extract_interests(self, prompt: str) -> InterestExtractionResult:
        return InterestExtractionResult()


def _uow_override(llm_client: LLMClient) -> Callable[[Request], AsyncGenerator[UnitOfWork, None]]:
    """Return a get_uow dependency override that injects InterestService(session, llm_client)."""

    def interest_service_factory(session: AsyncSession) -> InterestService:
        return InterestService(session, llm_client)

    async def override(request: Request) -> AsyncGenerator[UnitOfWork, None]:
        session_maker = get_session_maker()
        async with session_maker() as session:
            services = dict(request.app.state.services)
            services["interest_service"] = interest_service_factory
            try:
                yield UnitOfWork(session, services)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return override


class TestRateLimits:
    """Test API rate limit behavior."""

    @pytest.mark.asyncio
    async def test_register_rate_limited(self, async_http_client: AsyncClient) -> None:
        """Test that registration is rate-limited."""
        # Arrange
        statuses: list[int] = []
        for i in range(6):
            payload = RegisterUserRequest(
                email=f"rate-limit-{i}@example.com",
                password="password123",
                confirm_password="password123",
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
            email="limit-user@example.com",
            password="password123",
            confirm_password="password123",
        ).model_dump()
        await async_http_client.post("/api/auth/register", json=register_payload)
        login_payload = LoginUserRequest(
            email="limit-user@example.com", password="password123"
        ).model_dump()
        login_response = await async_http_client.post("/api/auth/login", json=login_payload)
        token = AccessTokenResponse.model_validate(login_response.json()).access_token

        async_app.dependency_overrides[get_uow] = _uow_override(MockLLMClient())

        extract_payload = InterestExtractionRequest(prompt="Testing rate limits").model_dump()
        statuses: list[int] = []

        # Act
        for i in range(6):
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
                InterestExtractionResponse.model_validate(response.json())

        # Assert
        assert statuses[:5] == [status.HTTP_200_OK] * 5
        assert statuses[5] == status.HTTP_429_TOO_MANY_REQUESTS

        second_register = RegisterUserRequest(
            email="limit-user-2@example.com",
            password="password123",
            confirm_password="password123",
        ).model_dump()
        await async_http_client.post("/api/auth/register", json=second_register)
        second_login_payload = LoginUserRequest(
            email="limit-user-2@example.com", password="password123"
        ).model_dump()
        second_login = await async_http_client.post("/api/auth/login", json=second_login_payload)
        second_token = AccessTokenResponse.model_validate(second_login.json()).access_token

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
        InterestExtractionResponse.model_validate(second_response.json())

        async_app.dependency_overrides.pop(get_uow, None)
