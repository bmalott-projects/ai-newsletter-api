from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from app.core import lifespan as lifespan_module
from app.core.lifespan import lifespan, verify_database_connection


@pytest.mark.asyncio
async def test_verify_database_connection_success() -> None:
    """Test that database connection verification succeeds when DB is available."""
    with patch("app.core.lifespan.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_execute = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.execute = mock_execute
        mock_engine.connect.return_value = mock_conn

        await verify_database_connection()

        mock_engine.connect.assert_called_once()
        mock_execute.assert_called_once()


@pytest.mark.asyncio
async def test_verify_database_connection_failure() -> None:
    """Test that database connection verification raises on failure."""
    with patch("app.core.lifespan.engine") as mock_engine:
        mock_engine.connect.side_effect = Exception("Connection failed")
        with pytest.raises(RuntimeError, match="Failed to connect to database"):
            await verify_database_connection()


@pytest.mark.asyncio
async def test_lifespan_skips_db_check_in_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that lifespan skips database verification in test environment."""
    monkeypatch.setattr(lifespan_module.settings, "environment", "test")
    with patch("app.core.lifespan.verify_database_connection") as mock_verify:
        app = FastAPI()

        async with lifespan(app):
            pass

        mock_verify.assert_not_called()


@pytest.mark.asyncio
async def test_lifespan_verifies_db_in_non_test_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that lifespan verifies database in non-test environments."""
    monkeypatch.setattr(lifespan_module.settings, "environment", "local")
    with patch("app.core.lifespan.verify_database_connection") as mock_verify:
        mock_verify.return_value = None
        app = FastAPI()

        async with lifespan(app):
            pass

        mock_verify.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_disposes_engine_on_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that lifespan disposes engine on shutdown."""
    monkeypatch.setattr(lifespan_module.settings, "environment", "test")
    with patch("app.core.lifespan.engine") as mock_engine:
        mock_engine.dispose = AsyncMock()
        app = FastAPI()

        async with lifespan(app):
            pass

        mock_engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_disposes_engine_even_if_startup_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that engine is disposed even if startup verification fails."""
    monkeypatch.setattr(lifespan_module.settings, "environment", "local")
    with patch("app.core.lifespan.engine") as mock_engine:
        mock_engine.dispose = AsyncMock()
        with patch(
            "app.core.lifespan.verify_database_connection",
            side_effect=RuntimeError("DB failed"),
        ):
            app = FastAPI()

            with pytest.raises(RuntimeError):
                async with lifespan(app):
                    pass

            # Engine should still be disposed even if startup fails
            mock_engine.dispose.assert_called_once()
