from __future__ import annotations

import logging
import sys
from importlib.metadata import PackageNotFoundError, version

from fastapi import FastAPI

from app.api.router import router as api_router
from app.core.config import MissingRequiredSettingsError
from app.core.lifespan import lifespan
from app.core.logging import configure_logging

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
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
