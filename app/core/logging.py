from __future__ import annotations

import logging

from app.core.config import settings


# Centralized app logging configuration (format + level).
def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
