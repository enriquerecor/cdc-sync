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


@router.get(
    "",
    response_model=list[WorkerResponse],
    summary="Listar workers",
    description="Devuelve los workers administrativos registrados.",
    response_description="Workers disponibles en el control plane.",
)
def list_workers(
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> list[WorkerResponse]:
    workers = execute_admin_operation(use_case.list_workers)
    return [WorkerResponse.from_domain(worker) for worker in workers]


@router.post(
    "",
    response_model=WorkerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear worker",
    description=(
        "Registra un worker stateless identificado por WORKER_ID. Si "
        "kafka_group_id no se informa, el runtime deriva un grupo estable."
    ),
    response_description="Worker creado.",
    responses={
        409: {"description": "Worker o group_id efectivo duplicado."},
        422: {"description": "Payload incompatible."},
    },
)
def create_worker(
    request: WorkerRequest,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> WorkerResponse:
    worker = execute_admin_operation(lambda: use_case.create_worker(request.to_dto()))
    return WorkerResponse.from_domain(worker)


@router.get(
    "/{worker_internal_id}",
    response_model=WorkerResponse,
    summary="Consultar worker",
    description="Devuelve un worker por su UUID interno administrativo.",
    response_description="Worker encontrado.",
    responses={404: {"description": "Worker inexistente."}},
)
def get_worker(
    worker_internal_id: UUID,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> WorkerResponse:
    worker = execute_admin_operation(lambda: use_case.get_worker(worker_internal_id))
    return WorkerResponse.from_domain(worker)


@router.put(
    "/{worker_internal_id}",
    response_model=WorkerResponse,
    summary="Actualizar worker",
    description=(
        "Actualiza la identidad administrativa, estado y group_id opcional "
        "de un worker existente."
    ),
    response_description="Worker actualizado.",
    responses={
        404: {"description": "Worker inexistente."},
        409: {"description": "Worker o group_id efectivo duplicado."},
        422: {"description": "Payload incompatible."},
    },
)
def update_worker(
    worker_internal_id: UUID,
    request: WorkerRequest,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> WorkerResponse:
    worker = execute_admin_operation(
        lambda: use_case.update_worker(worker_internal_id, request.to_dto())
    )
    return WorkerResponse.from_domain(worker)


@router.delete(
    "/{worker_internal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar worker",
    description="Elimina un worker administrativo por su UUID interno.",
    responses={
        204: {"description": "Worker eliminado."},
        404: {"description": "Worker inexistente."},
    },
)
def delete_worker(
    worker_internal_id: UUID,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> Response:
    execute_admin_operation(lambda: use_case.delete_worker(worker_internal_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{worker_internal_id}/config-assignment",
    response_model=AssignmentResponse,
    summary="Asignar configuración efectiva",
    description=(
        "Publica la configuración efectiva que el worker cargará en el "
        "siguiente arranque manual."
    ),
    response_description="Asignación efectiva persistida.",
    responses={
        404: {"description": "Worker o configuración inexistente."},
        422: {"description": "Asignación incompatible."},
    },
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
