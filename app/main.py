from __future__ import annotations

import logging
import sys
import types
from importlib.metadata import PackageNotFoundError, version
from typing import cast

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ExceptionHandler

from app.api.router import router as api_router
from app.core.config import InvalidSettingsError, MissingRequiredSettingsError
from app.core.errors import (
    http_exception_handler,
    rate_limit_exception_handler,
    request_validation_exception_handler,
    unhandled_exception_handler,
)
from app.core.lifespan import lifespan
from app.core.logging import configure_logging
from app.core.rate_limit import limiter
from app.llm.client import OpenAIClient
from app.services.auth_service import auth_service_factory_provider
from app.services.interest_service import interest_service_factory_provider

# Import settings - this may raise MissingRequiredSettingsError
try:
    from app.core.config import settings
except MissingRequiredSettingsError as e:
    print("ERROR: Missing required environment variables:", file=sys.stderr)
    for field in e.missing_fields:
        print(f"  - {field}", file=sys.stderr)
    print(
        "\nPlease set these in your .env file (see env.example for reference)",
        file=sys.stderr,
    )
    sys.exit(1)
except InvalidSettingsError as e:
    print("ERROR: Invalid environment variable values:", file=sys.stderr)
    for field, message in e.invalid_fields:
        print(f"  - {field}: {message}", file=sys.stderr)
    print(
        "\nPlease update these in your .env file (see env.example for reference)",
        file=sys.stderr,
    )
    sys.exit(1)


def create_app() -> FastAPI:
    configure_logging()

    try:
        api_version = version("ai-newsletter-api")
    except PackageNotFoundError:
        api_version = "0.1.0"  # Fallback if package not installed
        logging.warning("ai-newsletter-api package not found, using fallback version 0.1.0")

    is_debug_mode = settings.environment == "local"
    app = FastAPI(
        title=settings.app_name,
        version=api_version,
        debug=is_debug_mode,
        lifespan=lifespan,
    )
    app.add_exception_handler(
        StarletteHTTPException, cast(ExceptionHandler, http_exception_handler)
    )
    app.add_exception_handler(
        RequestValidationError, cast(ExceptionHandler, request_validation_exception_handler)
    )
    app.add_exception_handler(
        RateLimitExceeded, cast(ExceptionHandler, rate_limit_exception_handler)
    )
    app.add_exception_handler(Exception, cast(ExceptionHandler, unhandled_exception_handler))
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(api_router, prefix="/api")
    openai_client = OpenAIClient()

    _services = {
        "auth_service": auth_service_factory_provider(),
        "interest_service": interest_service_factory_provider(openai_client),
    }
    app.state.services = types.MappingProxyType(_services)

    return app


app = create_app()
