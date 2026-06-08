from __future__ import annotations

from uuid import UUID

from cdc_sync_api.application.dto.cdc_connector_dto import (
    CdcConnectorCompileRequest,
    MaterializedCdcConnectorDto,
)
from cdc_sync_api.application.errors import ControlPlaneNotFoundError
from cdc_sync_api.application.ports.control_plane_repository import (
    ControlPlaneRepository,
)
from cdc_sync_api.application.ports.kafka_connect_client import KafkaConnectClient
from cdc_sync_api.application.services.cdc_connector_compiler_registry import (
    CdcConnectorCompilerRegistry,
)
from cdc_sync_api.domain.control_plane import (
    ControlPlaneValidationError,
    SecretReference,
    SourceConnection,
    SyncConfig,
)


class MaterializeCdcConnectorUseCase:
    def __init__(
        self,
        repository: ControlPlaneRepository,
        compiler_registry: CdcConnectorCompilerRegistry,
        kafka_connect_client: KafkaConnectClient,
    ) -> None:
        self._repository = repository
        self._compiler_registry = compiler_registry
        self._kafka_connect_client = kafka_connect_client

    def materialize_source_connector(
        self,
        source_connection_id: UUID,
    ) -> MaterializedCdcConnectorDto:
        source_connection = self._get_source_connection(source_connection_id)
        credentials = self._get_credentials(source_connection)
        enabled_configs = self._enabled_configs_for_source(source_connection)
        compiler = self._compiler_registry.get(source_connection.source_type)
        compiled_connector = compiler.compile(
            CdcConnectorCompileRequest(
                source_connection=source_connection,
                credentials=credentials,
                configs=enabled_configs,
            )
        )

        self._kafka_connect_client.put_connector_config(
            compiled_connector.connector_name,
            compiled_connector.config,
        )

        return MaterializedCdcConnectorDto.from_compiled(compiled_connector)

    def _get_source_connection(
        self,
        source_connection_id: UUID,
    ) -> SourceConnection:
        source_connection = self._repository.get_source_connection(source_connection_id)
        if source_connection is not None:
            return source_connection

        raise ControlPlaneNotFoundError("No existe la conexión de origen indicada")

    def _get_credentials(
        self,
        source_connection: SourceConnection,
    ) -> SecretReference:
        credentials = self._repository.get_secret_reference(
            source_connection.credentials_secret_id
        )
        if credentials is not None:
            return credentials

        raise ControlPlaneValidationError(
            "No existen credenciales para la conexión de origen indicada"
        )

    def _enabled_configs_for_source(
        self,
        source_connection: SourceConnection,
    ) -> tuple[SyncConfig, ...]:
        return tuple(
            config
            for config in self._repository.list_configs()
            if config.enabled and config.source_connection_id == source_connection.id
        )
