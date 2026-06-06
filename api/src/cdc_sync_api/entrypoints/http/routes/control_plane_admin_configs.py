from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from cdc_sync_api.application.use_cases.manage_control_plane import (
    ManageControlPlaneUseCase,
)
from cdc_sync_api.entrypoints.http.dependencies import (
    get_control_plane_admin_use_case,
)
from cdc_sync_api.entrypoints.http.routes.control_plane_admin_errors import (
    execute_admin_operation,
)
from cdc_sync_api.entrypoints.http.schemas.control_plane_admin import (
    SyncConfigRequest,
    SyncConfigResponse,
)

router = APIRouter(prefix="/configs")


@router.get("", response_model=list[SyncConfigResponse])
def list_configs(
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> list[SyncConfigResponse]:
    configs = execute_admin_operation(use_case.list_configs)
    return [SyncConfigResponse.from_domain(config) for config in configs]


@router.post(
    "",
    response_model=SyncConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_config(
    request: SyncConfigRequest,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> SyncConfigResponse:
    config = execute_admin_operation(lambda: use_case.create_config(request.to_dto()))
    return SyncConfigResponse.from_domain(config)


@router.get("/{config_id}", response_model=SyncConfigResponse)
def get_config(
    config_id: UUID,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> SyncConfigResponse:
    config = execute_admin_operation(lambda: use_case.get_config(config_id))
    return SyncConfigResponse.from_domain(config)


@router.put("/{config_id}", response_model=SyncConfigResponse)
def update_config(
    config_id: UUID,
    request: SyncConfigRequest,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> SyncConfigResponse:
    config = execute_admin_operation(
        lambda: use_case.update_config(config_id, request.to_dto())
    )
    return SyncConfigResponse.from_domain(config)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_config(
    config_id: UUID,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> Response:
    execute_admin_operation(lambda: use_case.delete_config(config_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
