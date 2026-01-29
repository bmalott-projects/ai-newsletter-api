from __future__ import annotations

from collections.abc import Callable
from typing import Final, ParamSpec, TypeVar, cast

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.auth import verify_token
from app.core.config import settings

DEFAULT_RATE_LIMIT: Final[str] = "120/minute"
HEALTH_RATE_LIMIT: Final[str] = "300/minute"
AUTH_REGISTER_RATE_LIMIT: Final[str] = "5/minute"
AUTH_LOGIN_RATE_LIMIT: Final[str] = "10/minute"
AUTH_DELETE_RATE_LIMIT: Final[str] = "2/minute"
INTEREST_EXTRACT_RATE_LIMIT: Final[str] = "5/minute"

P = ParamSpec("P")
R = TypeVar("R")
StrOrCallableStr = str | Callable[..., str]
BoolCallable = Callable[..., bool]
ErrorMessageValue = str | Callable[..., str]


def _get_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def rate_limit_ip_key(request: Request) -> str:
    return f"ip:{get_remote_address(request)}"


def rate_limit_user_or_ip_key(request: Request) -> str:
    token = _get_bearer_token(request)
    if token:
        payload = verify_token(token)
        if payload:
            user_id = payload.get("sub")
            if isinstance(user_id, str) and user_id:
                return f"user:{user_id}"
    return rate_limit_ip_key(request)


limiter = Limiter(
    key_func=rate_limit_user_or_ip_key,
    default_limits=[DEFAULT_RATE_LIMIT],
    storage_uri=settings.rate_limit_storage_url,
    in_memory_fallback_enabled=True,
    in_memory_fallback=[DEFAULT_RATE_LIMIT],
)


def limit(
    limit_value: StrOrCallableStr,
    *,
    key_func: Callable[..., str] | None = None,
    per_method: bool = False,
    methods: list[str] | None = None,
    error_message: ErrorMessageValue | None = None,
    exempt_when: BoolCallable | None = None,
    override_defaults: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Typed wrapper for SlowAPI's limit decorator."""
    limit_decorator = cast(
        Callable[..., Callable[[Callable[P, R]], Callable[P, R]]],
        limiter.limit,
    )
    return limit_decorator(
        limit_value,
        key_func=key_func,
        per_method=per_method,
        methods=methods,
        error_message=error_message,
        exempt_when=exempt_when,
        override_defaults=override_defaults,
    )
