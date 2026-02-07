"""Unit of Work: one transaction per request, session-scoped services from registry."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, cast

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session_maker
from app.services.auth_service import AuthService
from app.services.interest_service import InterestService


class UnitOfWork:
    """Holds the request's session and exposes session-scoped services from the registry."""

    def __init__(self, session: AsyncSession, services: dict[str, Any]) -> None:
        self._session = session
        self._services = services
        self._auth_service: AuthService | None = None
        self._interest_service: InterestService | None = None

    def _resolve(self, key: str) -> Any:
        service = self._services[key]
        if callable(service):
            return service(self._session)
        return service

    @property
    def auth_service(self) -> AuthService:
        """Session-scoped auth service."""
        if self._auth_service is None:
            resolved = cast(AuthService, self._resolve("auth_service"))
            self._auth_service = resolved
            return resolved
        return self._auth_service

    @property
    def interest_service(self) -> InterestService:
        """Session-scoped interest service."""
        if self._interest_service is None:
            resolved = cast(InterestService, self._resolve("interest_service"))
            self._interest_service = resolved
            return resolved
        return self._interest_service


async def get_uow(request: Request) -> AsyncIterator[UnitOfWork]:
    """Per-request dependency: one session, commit on success, rollback on exception."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield UnitOfWork(session, request.app.state.services)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
