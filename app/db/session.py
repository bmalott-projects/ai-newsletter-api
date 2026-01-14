from __future__ import annotations
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def create_engine() -> AsyncEngine:
    return create_async_engine(str(settings.database_url), pool_pre_ping=True)


engine = create_engine()
SessionLocal = async_sessionmaker[AsyncSession](
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
