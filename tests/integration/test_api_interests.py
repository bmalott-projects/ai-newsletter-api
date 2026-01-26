"""Integration tests for interest extraction API endpoint.

These tests use a mocked LLM client to avoid real API calls and costs.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from app.api.interests import get_llm_client
from app.llm.client import LLMClient
from app.llm.schemas import InterestExtractionResult


class MockLLMClient(LLMClient):
    """Mock LLM client for integration tests."""

    def __init__(self, result: InterestExtractionResult | None = None) -> None:
        """Initialize mock with optional predefined result."""
        self.result = result or InterestExtractionResult()

    async def extract_interests(self, prompt: str) -> InterestExtractionResult:
        """Mock implementation that returns predefined result."""
        return self.result


@pytest.mark.asyncio
async def test_extract_interests_success(
    async_http_client: AsyncClient, async_app: FastAPI
) -> None:
    """Test successful interest extraction via API."""
    # Arrange: Register and login to get token
    user_data = {"email": "test@example.com", "password": "password123"}
    await async_http_client.post("/api/auth/register", json=user_data)
    login_response = await async_http_client.post("/api/auth/login", json=user_data)
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Mock LLM client
    expected_result = InterestExtractionResult(
        add_interests=["Python", "FastAPI"], remove_interests=["JavaScript"]
    )
    mock_client = MockLLMClient(result=expected_result)
    async_app.dependency_overrides[get_llm_client] = lambda: mock_client

    request_data = {"prompt": "I'm interested in Python and FastAPI, but not JavaScript"}

    # Act
    response = await async_http_client.post(
        "/api/interests/extract", json=request_data, headers=headers
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["add_interests"] == ["Python", "FastAPI"]
    assert response_data["remove_interests"] == ["JavaScript"]


@pytest.mark.asyncio
async def test_extract_interests_requires_authentication(
    async_http_client: AsyncClient,
) -> None:
    """Test that interest extraction requires authentication."""
    # Act
    response = await async_http_client.post("/api/interests/extract", json={"prompt": "test"})

    # Assert
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_extract_interests_validation_error(
    async_http_client: AsyncClient, async_app: FastAPI
) -> None:
    """Test validation errors for invalid requests."""
    # Arrange: Register and login to get token
    user_data = {"email": "validation@example.com", "password": "password123"}
    await async_http_client.post("/api/auth/register", json=user_data)
    login_response = await async_http_client.post("/api/auth/login", json=user_data)
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Mock LLM client
    mock_client = MockLLMClient()
    async_app.dependency_overrides[get_llm_client] = lambda: mock_client

    # Test empty prompt
    response = await async_http_client.post(
        "/api/interests/extract", json={"prompt": ""}, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    payload = response.json()
    assert payload["error"] == "validation_error"
    assert payload["message"] == "Request validation failed"

    # Test missing prompt
    response = await async_http_client.post("/api/interests/extract", json={}, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    payload = response.json()
    assert payload["error"] == "validation_error"
    assert payload["message"] == "Request validation failed"

    # Test prompt too long
    long_prompt = "x" * 501
    response = await async_http_client.post(
        "/api/interests/extract", json={"prompt": long_prompt}, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    payload = response.json()
    assert payload["error"] == "validation_error"
    assert payload["message"] == "Request validation failed"
