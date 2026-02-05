"""Meta API endpoints (e.g. health)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.schemas.meta_response_models import HealthResponse
from app.core.rate_limit import HEALTH_RATE_LIMIT, limit, rate_limit_ip_key

router = APIRouter()


@router.get("/health")
@limit(HEALTH_RATE_LIMIT, key_func=rate_limit_ip_key)
def health(request: Request) -> HealthResponse:
    """Check the health of the application."""
    return HealthResponse(status="ok")
