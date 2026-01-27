from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
