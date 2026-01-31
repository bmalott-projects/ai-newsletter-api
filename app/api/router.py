from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.auth_api import router as auth_router
from app.api.interests_api import router as interests_router
from app.api.openapi_responses import rate_limited_response
from app.api.schemas.meta import HealthResponse
from app.core.rate_limit import HEALTH_RATE_LIMIT, limit, rate_limit_ip_key

router = APIRouter()


@router.get(
    "/health",
    tags=["meta"],
    summary="Health check",
    response_model=HealthResponse,
    responses=rate_limited_response(),
)
@limit(HEALTH_RATE_LIMIT, key_func=rate_limit_ip_key)
def health(request: Request) -> HealthResponse:
    """Check the health of the application."""
    return HealthResponse(status="ok")


# Include sub-routers
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(interests_router, prefix="/interests", tags=["interests"])
