from fastapi import FastAPI

from cdc_sync_api.entrypoints.http.routes.control_plane_admin import (
    router as control_plane_admin_router,
)
from cdc_sync_api.entrypoints.http.routes.health import router as health_router
from cdc_sync_api.entrypoints.http.routes.root import router as root_router
from cdc_sync_api.entrypoints.http.routes.worker_runtime_config import (
    router as worker_runtime_config_router,
)
from cdc_sync_api.shared.settings import get_settings

OPENAPI_TAGS = [
    {
        "name": "system",
        "description": "Operaciones de salud y descubrimiento básico de la API.",
    },
    {
        "name": "control-plane-admin",
        "description": (
            "Gestión administrativa de workers, conexiones, destinos, "
            "configuraciones, asignaciones efectivas y materialización CDC."
        ),
    },
    {
        "name": "worker-runtime",
        "description": (
            "Contrato runtime que consume cada worker stateless al arrancar "
            "con su WORKER_ID."
        ),
    },
]


def build_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.api_name,
        version=settings.api_version,
        description=(
            "Control plane REST de cdc-sync. La especificación OpenAPI es la "
            "fuente pública para frontend, worker y herramientas como Postman."
        ),
        openapi_tags=OPENAPI_TAGS,
    )
    app.include_router(root_router)
    app.include_router(health_router)
    app.include_router(worker_runtime_config_router)
    app.include_router(control_plane_admin_router)
    return app
