"""Integration tests for API rate limiting."""

from __future__ import annotations

import pytest
from fastapi import status
from httpx import AsyncClient


class TestRateLimits:
    """Test API rate limit behavior."""

    @pytest.mark.asyncio
    async def test_register_rate_limited(self, async_http_client: AsyncClient) -> None:
        """Test that repeated registration attempts trigger rate limiting."""
        statuses: list[int] = []
        for i in range(6):
            user_data = {"email": f"rate-limit-{i}@example.com", "password": "password123"}
            response = await async_http_client.post("/api/auth/register", json=user_data)
            statuses.append(response.status_code)

        assert statuses[:5] == [status.HTTP_201_CREATED] * 5
        assert statuses[5] == status.HTTP_429_TOO_MANY_REQUESTS
