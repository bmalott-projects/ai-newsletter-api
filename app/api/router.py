from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.interests import router as interests_router

router = APIRouter()


@router.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# Include sub-routers
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(interests_router, prefix="/interests", tags=["interests"])
