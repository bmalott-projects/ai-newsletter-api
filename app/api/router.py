from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.api.auth_api import router as auth_router
from app.api.interests_api import router as interests_router
from app.api.schemas.meta import HealthResponse
from app.core.errors import ErrorResponse
from app.core.rate_limit import HEALTH_RATE_LIMIT, limit, rate_limit_ip_key

router = APIRouter()


@router.get(
    "/health",
    tags=["meta"],
    summary="Health check",
    response_model=HealthResponse,
    responses={
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": ErrorResponse,
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "examples": {
                        "rate_limited": {
                            "summary": "Too many requests",
                            "value": {
                                "error": "rate_limited",
                                "message": "Too many requests",
                            },
                        }
                    }
                }
            },
        }
    },
)
@limit(HEALTH_RATE_LIMIT, key_func=rate_limit_ip_key)
def health(request: Request) -> HealthResponse:
    """Check the health of the application."""
    return HealthResponse(status="ok")


# Include sub-routers
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(interests_router, prefix="/interests", tags=["interests"])
