from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.auth import router as auth_router
from app.api.interests import router as interests_router

router = APIRouter()


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str


@router.get("/health", tags=["meta"])
def health() -> HealthResponse:
    """Check the health of the application."""
    return HealthResponse(status="ok")


# Include sub-routers
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(interests_router, prefix="/interests", tags=["interests"])
