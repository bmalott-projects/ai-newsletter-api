from importlib.metadata import version

from fastapi import FastAPI

from app.api.router import router as api_router
from app.core.config import settings
from app.core.lifespan import lifespan


def create_app() -> FastAPI:
    api_version = version("ai-newsletter-api")
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
