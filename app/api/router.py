from __future__ import annotations

from fastapi import APIRouter

from app.api.auth_api import router as auth_router
from app.api.interests_api import router as interests_router
from app.api.meta_api import router as meta_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(interests_router, prefix="/interests", tags=["interests"])
router.include_router(meta_router, prefix="/meta", tags=["meta"])
