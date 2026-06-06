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
    DestinationCreateRequest,
    DestinationResponse,
    DestinationUpdateRequest,
    SourceConnectionCreateRequest,
    SourceConnectionResponse,
    SourceConnectionUpdateRequest,
)

router = APIRouter()


@router.get(
    "/source-connections",
    response_model=list[SourceConnectionResponse],
)
def list_source_connections(
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> list[SourceConnectionResponse]:
    source_connections = execute_admin_operation(use_case.list_source_connections)
    return [
        SourceConnectionResponse.from_domain(source_connection)
        for source_connection in source_connections
    ]


@router.post(
    "/source-connections",
    response_model=SourceConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_source_connection(
    request: SourceConnectionCreateRequest,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> SourceConnectionResponse:
    source_connection = execute_admin_operation(
        lambda: use_case.create_source_connection(request.to_dto())
    )
    return SourceConnectionResponse.from_domain(source_connection)


@router.get(
    "/source-connections/{source_connection_id}",
    response_model=SourceConnectionResponse,
)
def get_source_connection(
    source_connection_id: UUID,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> SourceConnectionResponse:
    source_connection = execute_admin_operation(
        lambda: use_case.get_source_connection(source_connection_id)
    )
    return SourceConnectionResponse.from_domain(source_connection)


@router.put(
    "/source-connections/{source_connection_id}",
    response_model=SourceConnectionResponse,
)
def update_source_connection(
    source_connection_id: UUID,
    request: SourceConnectionUpdateRequest,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> SourceConnectionResponse:
    source_connection = execute_admin_operation(
        lambda: use_case.update_source_connection(
            source_connection_id,
            request.to_dto(),
        )
    )
    return SourceConnectionResponse.from_domain(source_connection)


@router.delete(
    "/source-connections/{source_connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_source_connection(
    source_connection_id: UUID,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> Response:
    execute_admin_operation(
        lambda: use_case.delete_source_connection(source_connection_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/destinations", response_model=list[DestinationResponse])
def list_destinations(
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> list[DestinationResponse]:
    destinations = execute_admin_operation(use_case.list_destinations)
    return [
        DestinationResponse.from_domain(destination)
        for destination in destinations
    ]


@router.post(
    "/destinations",
    response_model=DestinationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_destination(
    request: DestinationCreateRequest,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> DestinationResponse:
    destination = execute_admin_operation(
        lambda: use_case.create_destination(request.to_dto())
    )
    return DestinationResponse.from_domain(destination)


@router.get("/destinations/{destination_id}", response_model=DestinationResponse)
def get_destination(
    destination_id: UUID,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> DestinationResponse:
    destination = execute_admin_operation(lambda: use_case.get_destination(destination_id))
    return DestinationResponse.from_domain(destination)


@router.put("/destinations/{destination_id}", response_model=DestinationResponse)
def update_destination(
    destination_id: UUID,
    request: DestinationUpdateRequest,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> DestinationResponse:
    destination = execute_admin_operation(
        lambda: use_case.update_destination(destination_id, request.to_dto())
    )
    return DestinationResponse.from_domain(destination)


@router.delete(
    "/destinations/{destination_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_destination(
    destination_id: UUID,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> Response:
    execute_admin_operation(lambda: use_case.delete_destination(destination_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
