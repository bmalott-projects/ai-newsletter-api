from __future__ import annotations

from fastapi import FastAPI

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text

from app.core.logging import configure_logging
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan context manager for startup/shutdown events."""
    # Startup
    configure_logging()
    await verify_database_connection()
    yield
    # Shutdown
    await engine.dispose()


async def verify_database_connection() -> None:
    """Verify database connectivity at startup. Raises if connection fails."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        raise RuntimeError(f"Failed to connect to database: {e}") from e
