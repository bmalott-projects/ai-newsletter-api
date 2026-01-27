from __future__ import annotations

from fastapi import APIRouter

from app.api.auth_api import router as auth_router
from app.api.interests_api import router as interests_router
from app.api.schemas.meta import HealthResponse

router = APIRouter()


@router.get("/health", tags=["meta"])
def health() -> HealthResponse:
    """Check the health of the application."""
    return HealthResponse(status="ok")


# Include sub-routers
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(interests_router, prefix="/interests", tags=["interests"])
