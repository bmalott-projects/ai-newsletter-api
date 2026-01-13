from fastapi import FastAPI

from app.api.router import router as api_router
from app.core.config import settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.app_name)
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()

