from __future__ import annotations

from cdc_sync_api.application.dto.worker_runtime_config_dto import (
    RuntimeDestinationColumnDto,
    RuntimeDestinationCredentialsDto,
    RuntimeDestinationDto,
    RuntimeKafkaDto,
    RuntimeTableDestinationDto,
    RuntimeTableDto,
    RuntimeTableSourceDto,
    RuntimeTableSyncDto,
    RuntimeWorkerDto,
    WorkerRuntimeConfigDto,
)
from cdc_sync_api.application.errors import ControlPlaneNotFoundError
from cdc_sync_api.application.ports.control_plane_repository import (
    ControlPlaneRepository,
)
from cdc_sync_api.application.services.worker_kafka_identity import (
    effective_worker_kafka_group_id,
)
from cdc_sync_api.domain.control_plane import (
    ConfiguredTable,
    ControlPlaneValidationError,
    Destination,
    DestinationType,
    SecretReference,
    SourceConnection,
    SourceType,
    SyncConfig,
    Worker,
)

CONTRACT_VERSION = 1
CLICKHOUSE_RUNTIME_ADAPTER = "clickhouse"
SOURCE_RUNTIME_ADAPTERS = {
    SourceType.POSTGRESQL: "debezium_postgres",
}


class GetWorkerRuntimeConfigUseCase:
    def __init__(
        self,
        repository: ControlPlaneRepository,
        *,
        kafka_bootstrap_servers: str,
        kafka_client_id_prefix: str,
        kafka_auto_offset_reset: str,
        kafka_poll_timeout_ms: int,
    ) -> None:
        self._repository = repository
        self._kafka_bootstrap_servers = _ensure_non_empty_text(
            kafka_bootstrap_servers,
            "kafka_bootstrap_servers",
        )
        self._kafka_client_id_prefix = _ensure_non_empty_text(
            kafka_client_id_prefix,
            "kafka_client_id_prefix",
        )
        self._kafka_auto_offset_reset = _ensure_non_empty_text(
            kafka_auto_offset_reset,
            "kafka_auto_offset_reset",
        )
        self._kafka_poll_timeout_ms = _ensure_positive_int(
            kafka_poll_timeout_ms,
            "kafka_poll_timeout_ms",
        )

    def get_config(self, worker_id: str) -> WorkerRuntimeConfigDto:
        normalized_worker_id = _ensure_non_empty_text(worker_id, "worker_id")
        worker = self._get_worker(normalized_worker_id)
        self._ensure_worker_enabled(worker)
        assignment = self._repository.get_assignment_for_worker(worker.worker_id)
        if assignment is None:
            raise ControlPlaneNotFoundError(
                "No existe configuración efectiva para el worker indicado"
            )

        config = self._get_config(assignment.config_id)
        self._ensure_config_enabled(config)
        source_connection = self._get_source_connection(config)
        destination = self._get_destination(config)
        destination_credentials = self._get_destination_credentials(destination)
        enabled_tables = self._enabled_tables(config)

        return WorkerRuntimeConfigDto(
            contract_version=CONTRACT_VERSION,
            worker=RuntimeWorkerDto(worker_id=worker.worker_id),
            kafka=self._build_kafka(worker, enabled_tables),
            destination=self._build_destination(destination, destination_credentials),
            tables=self._build_tables(source_connection, config, enabled_tables),
        )

    def _get_worker(self, worker_id: str) -> Worker:
        worker = self._repository.get_worker_by_identifier(worker_id)
        if worker is not None:
            return worker

        raise ControlPlaneNotFoundError("No existe el worker indicado")

    def _ensure_worker_enabled(self, worker: Worker) -> None:
        if worker.enabled:
            return

        raise ControlPlaneValidationError("El worker indicado está deshabilitado")

    def _get_config(self, config_id) -> SyncConfig:
        config = self._repository.get_config(config_id)
        if config is not None:
            return config

        raise ControlPlaneValidationError(
            "La configuración administrativa efectiva referencia una configuración inexistente"
        )

    def _ensure_config_enabled(self, config: SyncConfig) -> None:
        if config.enabled:
            return

        raise ControlPlaneValidationError(
            "La configuración efectiva del worker está deshabilitada"
        )

    def _get_source_connection(self, config: SyncConfig) -> SourceConnection:
        source_connection = self._repository.get_source_connection(
            config.source_connection_id,
        )
        if source_connection is not None:
            return source_connection

        raise ControlPlaneValidationError(
            "La configuración administrativa efectiva referencia un origen inexistente"
        )

    def _get_destination(self, config: SyncConfig) -> Destination:
        destination = self._repository.get_destination(config.destination_id)
        if destination is not None:
            return destination

        raise ControlPlaneValidationError(
            "La configuración administrativa efectiva referencia un destino inexistente"
        )

    def _get_destination_credentials(
        self,
        destination: Destination,
    ) -> RuntimeDestinationCredentialsDto:
        secret = self._repository.get_secret_reference(destination.credentials_secret_id)
        if secret is None:
            raise ControlPlaneValidationError(
                "No existen credenciales para el destino indicado"
            )

        return _destination_credentials(secret)

    def _enabled_tables(
        self,
        config: SyncConfig,
    ) -> tuple[ConfiguredTable, ...]:
        enabled_tables = tuple(table for table in config.tables if table.enabled)
        if enabled_tables:
            return enabled_tables

        raise ControlPlaneValidationError(
            "La configuración efectiva debe incluir al menos una tabla habilitada"
        )

    def _build_kafka(
        self,
        worker: Worker,
        tables: tuple[ConfiguredTable, ...],
    ) -> RuntimeKafkaDto:
        return RuntimeKafkaDto(
            bootstrap_servers=self._kafka_bootstrap_servers,
            client_id=f"{self._kafka_client_id_prefix}-{worker.worker_id}",
            group_id=effective_worker_kafka_group_id(worker),
            auto_offset_reset=self._kafka_auto_offset_reset,
            poll_timeout_ms=self._kafka_poll_timeout_ms,
            topics=_unique_topics(tables),
        )

    def _build_destination(
        self,
        destination: Destination,
        credentials: RuntimeDestinationCredentialsDto,
    ) -> RuntimeDestinationDto:
        if destination.destination_type is not DestinationType.CLICKHOUSE:
            raise ControlPlaneValidationError(
                "El contrato runtime solo soporta destino ClickHouse"
            )

        return RuntimeDestinationDto(
            adapter=CLICKHOUSE_RUNTIME_ADAPTER,
            host=destination.host,
            port=destination.port,
            secure=destination.secure,
            database=destination.database_name,
            credentials=credentials,
        )

    def _build_tables(
        self,
        source_connection: SourceConnection,
        config: SyncConfig,
        tables: tuple[ConfiguredTable, ...],
    ) -> dict[str, RuntimeTableDto]:
        source_adapter = _source_runtime_adapter(source_connection)
        return {
            table.logical_name: _build_table(source_adapter, config, table)
            for table in tables
        }


def _destination_credentials(secret: SecretReference) -> RuntimeDestinationCredentialsDto:
    payload = secret.inline_payload
    if payload is None:
        raise ControlPlaneValidationError(
            "Las credenciales del destino deben tener payload inline"
        )

    user = payload.get("user")
    password = payload.get("password")
    if user and password:
        return RuntimeDestinationCredentialsDto(user=user, password=password)

    raise ControlPlaneValidationError(
        "Las credenciales del destino deben incluir user y password"
    )


def _unique_topics(tables: tuple[ConfiguredTable, ...]) -> tuple[str, ...]:
    topics: list[str] = []
    seen_topics: set[str] = set()

    for table in tables:
        if table.cdc_topic in seen_topics:
            continue

        seen_topics.add(table.cdc_topic)
        topics.append(table.cdc_topic)

    return tuple(topics)


def _source_runtime_adapter(source_connection: SourceConnection) -> str:
    adapter = SOURCE_RUNTIME_ADAPTERS.get(source_connection.source_type)
    if adapter is not None:
        return adapter

    raise ControlPlaneValidationError(
        f"No existe adapter runtime para el origen '{source_connection.source_type.value}'"
    )


def _build_table(
    source_adapter: str,
    config: SyncConfig,
    table: ConfiguredTable,
) -> RuntimeTableDto:
    return RuntimeTableDto(
        enabled=True,
        source=RuntimeTableSourceDto(
            adapter=source_adapter,
            schema=table.source_schema,
            table=table.source_table,
            topic=table.cdc_topic,
        ),
        pk=table.primary_key_fields,
        sync=RuntimeTableSyncDto(mode=config.sync_mode.value),
        destination=RuntimeTableDestinationDto(
            table=table.destination_table,
            columns=tuple(
                RuntimeDestinationColumnDto(
                    name=column.name,
                    type=column.destination_type,
                    nullable=column.nullable,
                )
                for column in table.destination_columns
            ),
        ),
    )


def _ensure_non_empty_text(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} debe ser texto")

    normalized_value = value.strip()
    if normalized_value:
        return normalized_value

    raise ControlPlaneValidationError(f"{label} no puede estar vacío")


def _ensure_positive_int(value: int, label: str) -> int:
    if not isinstance(value, int):
        raise TypeError(f"{label} debe ser entero")

    if value > 0:
        return value

    raise ControlPlaneValidationError(f"{label} debe ser mayor que 0")
