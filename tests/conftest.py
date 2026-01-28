"""Pytest configuration and shared fixtures for integration tests."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import cast
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic import PostgresDsn
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core import config
from app.db.base import Base
from app.main import create_app


def _get_test_database_url() -> str:
    """Resolve the test database URL from env or default derivation."""
    env_url = os.getenv("TEST_DATABASE_URL")
    if env_url:
        return env_url

    # Fall back to deriving a test database URL from the main database URL.
    try:
        base_db_url = str(config.settings.database_url)
    except Exception as exc:
        raise RuntimeError(
            "TEST_DATABASE_URL is not set and config.settings.database_url "
            "could not be loaded to derive a default test database URL."
        ) from exc

    parsed_base = urlparse(base_db_url)
    base_db_name = parsed_base.path.lstrip("/") or "postgres"
    test_db_name = f"{base_db_name}_test"
    return parsed_base._replace(path=f"/{test_db_name}").geturl()


# Prefer an explicit test database URL from the environment.
test_database_url = _get_test_database_url()

_parsed_test = urlparse(test_database_url)
postgres_url = _parsed_test._replace(path="/postgres").geturl()

# Async fixtures (session-scoped, for async tests that need database access).


@pytest_asyncio.fixture(scope="session")
async def ensure_test_database() -> None:
    """Ensures the test database exists, creating it if necessary."""
    # Parse the test database URL to get the database name
    parsed = urlparse(test_database_url)
    test_db_name = parsed.path.lstrip("/")

    # Connect to the default 'postgres' database to create the test database
    admin_engine = create_async_engine(
        postgres_url, pool_pre_ping=True, echo=False, isolation_level="AUTOCOMMIT"
    )

    try:
        async with admin_engine.connect() as conn:
            # Check if database exists
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": test_db_name},
            )
            exists = result.scalar() is not None

            if not exists:
                # Create the database (must use autocommit for CREATE DATABASE)
                await conn.execute(text(f'CREATE DATABASE "{test_db_name}"'))
    finally:
        # Use sync dispose to avoid event loop issues
        admin_engine.sync_engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_engine(ensure_test_database: None) -> AsyncIterator[AsyncEngine]:
    """Creates a test database engine (reused across all tests)."""
    engine = create_async_engine(test_database_url, pool_pre_ping=True, echo=False)
    yield engine
    # Properly dispose async engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def setup_test_db(test_engine: AsyncEngine) -> AsyncIterator[None]:
    """Creates test database tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup: drop all tables after all tests
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="session")
async def test_session_maker(
    setup_test_db: None, test_engine: AsyncEngine
) -> async_sessionmaker[AsyncSession]:
    """Creates a session maker (reused across all tests)."""
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function")
async def db_session(
    test_session_maker: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Creates a database session for a test (function-scoped).
    Ensures that any data created during a test does not leak into other tests
    by deleting all rows from all tables after the test completes.
    """
    async with test_session_maker() as session:
        try:
            yield session
        finally:
            # Cleanup: remove all data so tests remain isolated
            for table in reversed(Base.metadata.sorted_tables):
                await session.execute(table.delete())
            await session.commit()


@pytest_asyncio.fixture(scope="session")
async def async_app(test_session_maker: async_sessionmaker[AsyncSession]) -> AsyncIterator[FastAPI]:
    """Creates FastAPI app for async tests with test database settings.
    It is reused across all tests that include it (session-scoped).

    Uses session-scoped engine and session maker to avoid event loop conflicts
    since AsyncClient runs in the same event loop as pytest-asyncio.
    """
    # Set test environment (directly modify settings since monkeypatch is function-scoped)
    config.settings.environment = "test"
    config.settings.database_url = cast(PostgresDsn, test_database_url)

    fastapi_app = create_app()

    yield fastapi_app


@pytest_asyncio.fixture(scope="function")
async def async_http_client(async_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Creates an async http client."""
    transport = ASGITransport(app=async_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# Synchronous fixtures (function-scoped, for synchronous tests that don't need database access)


@pytest.fixture(scope="function")
def app() -> FastAPI:
    """Creates a FastAPI app for synchronous tests (function-scoped).

    Use this for sync tests that don't need database access. Tests using this
    can run in parallel since they don't share an event loop.
    """
    # Set test environment
    config.settings.environment = "test"
    config.settings.database_url = cast(PostgresDsn, test_database_url)

    fastapi_app = create_app()

    return fastapi_app


@pytest.fixture(scope="function")
def http_client(app: FastAPI) -> TestClient:
    """Creates a synchronous http client (for synchronous tests, can run in parallel)."""
    return TestClient(app)
