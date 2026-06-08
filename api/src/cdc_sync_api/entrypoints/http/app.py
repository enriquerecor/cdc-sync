from fastapi import FastAPI

from cdc_sync_api.entrypoints.http.routes.control_plane_admin import (
    router as control_plane_admin_router,
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
    app.include_router(control_plane_admin_router)
    return app
