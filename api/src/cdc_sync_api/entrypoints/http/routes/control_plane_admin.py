from fastapi import APIRouter

from cdc_sync_api.entrypoints.http.routes.control_plane_admin_configs import (
    router as configs_router,
)
from cdc_sync_api.entrypoints.http.routes.control_plane_admin_connections import (
    router as connections_router,
)
from cdc_sync_api.entrypoints.http.routes.control_plane_admin_workers import (
    router as workers_router,
)

router = APIRouter(prefix="/api/v1", tags=["control-plane-admin"])
router.include_router(workers_router)
router.include_router(connections_router)
router.include_router(configs_router)
