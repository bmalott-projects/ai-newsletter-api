"""Integration tests for health API endpoint."""

from __future__ import annotations

import pytest
from fastapi import status
from httpx import AsyncClient

from app.api.schemas import HealthResponse


@pytest.mark.asyncio
async def test_health(async_http_client: AsyncClient) -> None:
    """Test that the health endpoint returns ok status."""
    # Act
    response = await async_http_client.get("/api/meta/health")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    parsed = HealthResponse.model_validate(response.json())
    assert parsed.status == "ok"
