from fastapi import APIRouter, Depends

from cdc_sync_api.application.use_cases.get_worker_runtime_config import (
    GetWorkerRuntimeConfigUseCase,
)
from cdc_sync_api.entrypoints.http.dependencies import (
    get_worker_runtime_config_use_case,
)
from cdc_sync_api.entrypoints.http.routes.control_plane_admin_errors import (
    execute_control_plane_operation,
)
from cdc_sync_api.entrypoints.http.schemas.worker_runtime_config import (
    WorkerRuntimeConfigResponse,
)

router = APIRouter(prefix="/workers", tags=["worker-runtime"])


@router.get("/{worker_id}/config", response_model=WorkerRuntimeConfigResponse)
def get_worker_runtime_config(
    worker_id: str,
    use_case: GetWorkerRuntimeConfigUseCase = Depends(
        get_worker_runtime_config_use_case
    ),
) -> WorkerRuntimeConfigResponse:
    config = execute_control_plane_operation(lambda: use_case.get_config(worker_id))
    return WorkerRuntimeConfigResponse.from_dto(config)
