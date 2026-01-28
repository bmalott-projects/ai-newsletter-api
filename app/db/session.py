from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None
_database_url: str | None = None


def _build_session_maker(
    database_url: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_maker = async_sessionmaker[AsyncSession](
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    return engine, session_maker


def get_engine() -> AsyncEngine:
    global _engine, _session_maker, _database_url
    database_url = str(settings.database_url)
    if _engine is None or _database_url != database_url:
        if _engine is not None:
            _engine.sync_engine.dispose()
        _engine, _session_maker = _build_session_maker(database_url)
        _database_url = database_url
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _session_maker is not None
    return _session_maker


async def get_db() -> AsyncIterator[AsyncSession]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session


async def get_db_transaction() -> AsyncIterator[AsyncSession]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
