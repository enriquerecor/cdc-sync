from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from cdc_sync_api.application.use_cases.manage_control_plane import (
    ManageControlPlaneUseCase,
)
from cdc_sync_api.application.use_cases.materialize_cdc_connector import (
    MaterializeCdcConnectorUseCase,
)
from cdc_sync_api.entrypoints.http.dependencies import (
    get_control_plane_admin_use_case,
    get_materialize_cdc_connector_use_case,
)
from cdc_sync_api.entrypoints.http.routes.control_plane_admin_errors import (
    execute_admin_operation,
)
from cdc_sync_api.entrypoints.http.schemas.control_plane_admin import (
    CdcConnectorMaterializationResponse,
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
    summary="Listar conexiones de origen",
    description="Devuelve las conexiones PostgreSQL administradas por el control plane.",
    response_description="Conexiones de origen disponibles.",
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
    summary="Crear conexión de origen",
    description=(
        "Registra una conexión PostgreSQL de origen. Las credenciales se "
        "aceptan solo en escritura y no se devuelven en la respuesta."
    ),
    response_description="Conexión de origen creada sin secretos.",
    responses={422: {"description": "Origen o credenciales no compatibles."}},
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
    summary="Consultar conexión de origen",
    description="Devuelve una conexión de origen por su UUID interno.",
    response_description="Conexión de origen encontrada sin secretos.",
    responses={404: {"description": "Conexión de origen inexistente."}},
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
    summary="Actualizar conexión de origen",
    description=(
        "Actualiza los datos de conexión PostgreSQL. Si se informan "
        "credenciales, reemplazan las credenciales actuales."
    ),
    response_description="Conexión de origen actualizada sin secretos.",
    responses={
        404: {"description": "Conexión de origen inexistente."},
        422: {"description": "Origen o credenciales no compatibles."},
    },
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


@router.put(
    "/source-connections/{source_connection_id}/cdc-connector",
    response_model=CdcConnectorMaterializationResponse,
    summary="Materializar conector CDC",
    description=(
        "Compila y aplica de forma idempotente el conector Debezium "
        "PostgreSQL asociado a la conexión de origen."
    ),
    response_description="Conector CDC materializado sin exponer credenciales.",
    responses={
        404: {"description": "Conexión de origen inexistente."},
        422: {"description": "Configuración CDC incompatible o incompleta."},
        502: {"description": "Kafka Connect no está disponible o rechaza la petición."},
    },
)
def materialize_source_cdc_connector(
    source_connection_id: UUID,
    use_case: MaterializeCdcConnectorUseCase = Depends(
        get_materialize_cdc_connector_use_case
    ),
) -> CdcConnectorMaterializationResponse:
    materialized_connector = execute_admin_operation(
        lambda: use_case.materialize_source_connector(source_connection_id)
    )
    return CdcConnectorMaterializationResponse.from_dto(materialized_connector)


@router.delete(
    "/source-connections/{source_connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar conexión de origen",
    description="Elimina una conexión de origen si no está referenciada por configs.",
    responses={
        204: {"description": "Conexión de origen eliminada."},
        404: {"description": "Conexión de origen inexistente."},
        409: {"description": "La conexión está referenciada por una config."},
    },
)
def delete_source_connection(
    source_connection_id: UUID,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> Response:
    execute_admin_operation(
        lambda: use_case.delete_source_connection(source_connection_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/destinations",
    response_model=list[DestinationResponse],
    summary="Listar destinos",
    description="Devuelve los destinos ClickHouse administrados por el control plane.",
    response_description="Destinos disponibles.",
)
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
    summary="Crear destino",
    description=(
        "Registra un destino ClickHouse. Las credenciales se aceptan solo "
        "en escritura y no se devuelven en la respuesta."
    ),
    response_description="Destino creado sin secretos.",
    responses={422: {"description": "Destino o credenciales no compatibles."}},
)
def create_destination(
    request: DestinationCreateRequest,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> DestinationResponse:
    destination = execute_admin_operation(
        lambda: use_case.create_destination(request.to_dto())
    )
    return DestinationResponse.from_domain(destination)


@router.get(
    "/destinations/{destination_id}",
    response_model=DestinationResponse,
    summary="Consultar destino",
    description="Devuelve un destino ClickHouse por su UUID interno.",
    response_description="Destino encontrado sin secretos.",
    responses={404: {"description": "Destino inexistente."}},
)
def get_destination(
    destination_id: UUID,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> DestinationResponse:
    destination = execute_admin_operation(lambda: use_case.get_destination(destination_id))
    return DestinationResponse.from_domain(destination)


@router.put(
    "/destinations/{destination_id}",
    response_model=DestinationResponse,
    summary="Actualizar destino",
    description=(
        "Actualiza un destino ClickHouse. Si se informan credenciales, "
        "reemplazan las credenciales actuales."
    ),
    response_description="Destino actualizado sin secretos.",
    responses={
        404: {"description": "Destino inexistente."},
        422: {"description": "Destino o credenciales no compatibles."},
    },
)
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
    summary="Eliminar destino",
    description="Elimina un destino si no está referenciado por configs.",
    responses={
        204: {"description": "Destino eliminado."},
        404: {"description": "Destino inexistente."},
        409: {"description": "El destino está referenciado por una config."},
    },
)
def delete_destination(
    destination_id: UUID,
    use_case: ManageControlPlaneUseCase = Depends(get_control_plane_admin_use_case),
) -> Response:
    execute_admin_operation(lambda: use_case.delete_destination(destination_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
