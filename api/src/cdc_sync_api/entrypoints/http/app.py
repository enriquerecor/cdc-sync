from fastapi import FastAPI

from cdc_sync_api.entrypoints.http.routes.editing_config import (
    router as editing_config_router,
)
from cdc_sync_api.entrypoints.http.routes.health import router as health_router
from cdc_sync_api.entrypoints.http.routes.root import router as root_router
from cdc_sync_api.shared.settings import get_settings


def build_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.api_name,
        version=settings.api_version,
    )
    app.include_router(root_router)
    app.include_router(health_router)
    app.include_router(editing_config_router)
    return app
