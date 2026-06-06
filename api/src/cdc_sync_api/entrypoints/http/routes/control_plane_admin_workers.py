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
    AssignmentRequest,
    AssignmentResponse,
    WorkerRequest,
    WorkerResponse,
)

router = APIRouter(prefix="/workers")


@router.get("", response_model=list[WorkerResponse])
def list_workers(
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> list[WorkerResponse]:
    workers = execute_admin_operation(use_case.list_workers)
    return [WorkerResponse.from_domain(worker) for worker in workers]


@router.post(
    "",
    response_model=WorkerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_worker(
    request: WorkerRequest,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> WorkerResponse:
    worker = execute_admin_operation(lambda: use_case.create_worker(request.to_dto()))
    return WorkerResponse.from_domain(worker)


@router.get("/{worker_internal_id}", response_model=WorkerResponse)
def get_worker(
    worker_internal_id: UUID,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> WorkerResponse:
    worker = execute_admin_operation(lambda: use_case.get_worker(worker_internal_id))
    return WorkerResponse.from_domain(worker)


@router.put("/{worker_internal_id}", response_model=WorkerResponse)
def update_worker(
    worker_internal_id: UUID,
    request: WorkerRequest,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> WorkerResponse:
    worker = execute_admin_operation(
        lambda: use_case.update_worker(worker_internal_id, request.to_dto())
    )
    return WorkerResponse.from_domain(worker)


@router.delete("/{worker_internal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_worker(
    worker_internal_id: UUID,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> Response:
    execute_admin_operation(lambda: use_case.delete_worker(worker_internal_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{worker_internal_id}/config-assignment",
    response_model=AssignmentResponse,
)
def assign_config_to_worker(
    worker_internal_id: UUID,
    request: AssignmentRequest,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> AssignmentResponse:
    assignment = execute_admin_operation(
        lambda: use_case.assign_config_to_worker(
            worker_internal_id,
            request.to_dto(),
        )
    )
    return AssignmentResponse.from_dto(assignment)
