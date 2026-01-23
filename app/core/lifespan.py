from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan context manager for startup/shutdown events."""
    try:
        # Startup
        if settings.environment != "test":
            await verify_database_connection()
        yield

        # Shutdown
    finally:
        await engine.dispose()


async def verify_database_connection() -> None:
    """Verify database connectivity at startup. Raises if connection fails."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        raise RuntimeError(f"Failed to connect to database: {e}") from e
