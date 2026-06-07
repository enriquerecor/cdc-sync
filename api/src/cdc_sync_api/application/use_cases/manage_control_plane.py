from __future__ import annotations

from uuid import UUID, uuid4

from cdc_sync_api.application.dto.control_plane_admin_dto import (
    AssignmentRequestDto,
    ConfiguredTableDto,
    CredentialsDto,
    DestinationColumnDto,
    DestinationCreateDto,
    DestinationUpdateDto,
    SourceConnectionCreateDto,
    SourceConnectionUpdateDto,
    SyncConfigRequestDto,
    WorkerRequestDto,
)
from cdc_sync_api.application.dto.control_plane_assignment_dto import (
    WorkerConfigAssignmentDto,
)
from cdc_sync_api.application.errors import (
    ControlPlaneConflictError,
    ControlPlaneNotFoundError,
)
from cdc_sync_api.application.ports.control_plane_repository import (
    ControlPlaneRepository,
)
from cdc_sync_api.application.services.worker_kafka_identity import (
    effective_worker_kafka_group_id,
)
from cdc_sync_api.domain.control_plane import (
    ConfiguredTable,
    Destination,
    DestinationColumn,
    SecretProvider,
    SecretReference,
    SourceConnection,
    SyncConfig,
    Worker,
    WorkerConfigAssignment,
)


class ManageControlPlaneUseCase:
    def __init__(self, repository: ControlPlaneRepository) -> None:
        self._repository = repository

    def list_workers(self) -> tuple[Worker, ...]:
        return self._repository.list_workers()

    def create_worker(self, request: WorkerRequestDto) -> Worker:
        worker = Worker(
            id=uuid4(),
            worker_id=request.worker_id,
            name=request.name,
            description=request.description,
            kafka_group_id=request.kafka_group_id,
            enabled=request.enabled,
        )
        self._ensure_unique_worker_kafka_group(worker)
        self._repository.save_worker(worker)
        return worker

    def get_worker(self, worker_id: UUID) -> Worker:
        return self._get_worker(worker_id)

    def update_worker(self, worker_id: UUID, request: WorkerRequestDto) -> Worker:
        self._get_worker(worker_id)
        worker = Worker(
            id=worker_id,
            worker_id=request.worker_id,
            name=request.name,
            description=request.description,
            kafka_group_id=request.kafka_group_id,
            enabled=request.enabled,
        )
        self._ensure_unique_worker_kafka_group(worker)

        updated = self._repository.update_worker(worker)
        if not updated:
            raise ControlPlaneNotFoundError("No existe el worker indicado")

        return worker

    def delete_worker(self, worker_id: UUID) -> None:
        deleted = self._repository.delete_worker(worker_id)
        if deleted:
            return

        raise ControlPlaneNotFoundError("No existe el worker indicado")

    def list_source_connections(self) -> tuple[SourceConnection, ...]:
        return self._repository.list_source_connections()

    def create_source_connection(
        self,
        request: SourceConnectionCreateDto,
    ) -> SourceConnection:
        source_connection_id = uuid4()
        credentials = _build_secret_reference(
            secret_id=uuid4(),
            name=f"source-credentials-{source_connection_id}",
            credentials=request.credentials,
        )
        source_connection = SourceConnection(
            id=source_connection_id,
            name=request.name,
            source_type=request.source_type,
            host=request.host,
            port=request.port,
            database_name=request.database_name,
            credentials_secret_id=credentials.id,
        )
        self._repository.save_source_connection_with_credentials(
            source_connection,
            credentials,
        )
        return source_connection

    def get_source_connection(self, source_connection_id: UUID) -> SourceConnection:
        return self._get_source_connection(source_connection_id)

    def update_source_connection(
        self,
        source_connection_id: UUID,
        request: SourceConnectionUpdateDto,
    ) -> SourceConnection:
        current_source_connection = self._get_source_connection(source_connection_id)
        credentials = _build_optional_secret_reference(
            secret_id=current_source_connection.credentials_secret_id,
            name=f"source-credentials-{source_connection_id}",
            credentials=request.credentials,
        )
        source_connection = SourceConnection(
            id=source_connection_id,
            name=request.name,
            source_type=request.source_type,
            host=request.host,
            port=request.port,
            database_name=request.database_name,
            credentials_secret_id=current_source_connection.credentials_secret_id,
        )

        updated = self._repository.update_source_connection(
            source_connection,
            credentials,
        )
        if not updated:
            raise ControlPlaneNotFoundError("No existe la conexión de origen indicada")

        return source_connection

    def delete_source_connection(self, source_connection_id: UUID) -> None:
        deleted = self._repository.delete_source_connection(source_connection_id)
        if deleted:
            return

        raise ControlPlaneNotFoundError("No existe la conexión de origen indicada")

    def list_destinations(self) -> tuple[Destination, ...]:
        return self._repository.list_destinations()

    def create_destination(self, request: DestinationCreateDto) -> Destination:
        destination_id = uuid4()
        credentials = _build_secret_reference(
            secret_id=uuid4(),
            name=f"destination-credentials-{destination_id}",
            credentials=request.credentials,
        )
        destination = Destination(
            id=destination_id,
            name=request.name,
            destination_type=request.destination_type,
            host=request.host,
            port=request.port,
            secure=request.secure,
            database_name=request.database_name,
            credentials_secret_id=credentials.id,
        )
        self._repository.save_destination_with_credentials(destination, credentials)
        return destination

    def get_destination(self, destination_id: UUID) -> Destination:
        return self._get_destination(destination_id)

    def update_destination(
        self,
        destination_id: UUID,
        request: DestinationUpdateDto,
    ) -> Destination:
        current_destination = self._get_destination(destination_id)
        credentials = _build_optional_secret_reference(
            secret_id=current_destination.credentials_secret_id,
            name=f"destination-credentials-{destination_id}",
            credentials=request.credentials,
        )
        destination = Destination(
            id=destination_id,
            name=request.name,
            destination_type=request.destination_type,
            host=request.host,
            port=request.port,
            secure=request.secure,
            database_name=request.database_name,
            credentials_secret_id=current_destination.credentials_secret_id,
        )

        updated = self._repository.update_destination(destination, credentials)
        if not updated:
            raise ControlPlaneNotFoundError("No existe el destino indicado")

        return destination

    def delete_destination(self, destination_id: UUID) -> None:
        deleted = self._repository.delete_destination(destination_id)
        if deleted:
            return

        raise ControlPlaneNotFoundError("No existe el destino indicado")

    def list_configs(self) -> tuple[SyncConfig, ...]:
        return self._repository.list_configs()

    def create_config(self, request: SyncConfigRequestDto) -> SyncConfig:
        self._ensure_config_references_exist(request)
        config = _build_sync_config(uuid4(), request)
        self._repository.save_config(config)
        return config

    def get_config(self, config_id: UUID) -> SyncConfig:
        return self._get_config(config_id)

    def update_config(
        self,
        config_id: UUID,
        request: SyncConfigRequestDto,
    ) -> SyncConfig:
        self._get_config(config_id)
        self._ensure_config_references_exist(request)
        config = _build_sync_config(config_id, request)

        updated = self._repository.update_config(config)
        if not updated:
            raise ControlPlaneNotFoundError("No existe la configuración indicada")

        return config

    def delete_config(self, config_id: UUID) -> None:
        deleted = self._repository.delete_config(config_id)
        if deleted:
            return

        raise ControlPlaneNotFoundError("No existe la configuración indicada")

    def assign_config_to_worker(
        self,
        worker_id: UUID,
        request: AssignmentRequestDto,
    ) -> WorkerConfigAssignmentDto:
        worker = self._get_worker(worker_id)
        config = self._get_config(request.config_id)
        assignment = WorkerConfigAssignment(worker_id=worker.id, config_id=config.id)
        self._repository.assign_config_to_worker(assignment)
        persisted_assignment = self._repository.get_assignment_for_worker(
            worker.worker_id,
        )

        if persisted_assignment is None:
            raise ControlPlaneNotFoundError(
                "No existe la asignación efectiva del worker indicado"
            )

        return persisted_assignment

    def _ensure_config_references_exist(self, request: SyncConfigRequestDto) -> None:
        self._get_source_connection(request.source_connection_id)
        self._get_destination(request.destination_id)

    def _ensure_unique_worker_kafka_group(self, worker: Worker) -> None:
        worker_group_id = effective_worker_kafka_group_id(worker)

        for existing_worker in self._repository.list_workers():
            if existing_worker.id == worker.id:
                continue

            existing_group_id = effective_worker_kafka_group_id(existing_worker)
            if existing_group_id != worker_group_id:
                continue

            raise ControlPlaneConflictError(
                f"El group_id efectivo de Kafka '{worker_group_id}' ya está asignado "
                f"al worker '{existing_worker.worker_id}'"
            )

    def _get_worker(self, worker_id: UUID) -> Worker:
        worker = self._repository.get_worker(worker_id)
        if worker is not None:
            return worker

        raise ControlPlaneNotFoundError("No existe el worker indicado")

    def _get_source_connection(self, source_connection_id: UUID) -> SourceConnection:
        source_connection = self._repository.get_source_connection(
            source_connection_id,
        )
        if source_connection is not None:
            return source_connection

        raise ControlPlaneNotFoundError("No existe la conexión de origen indicada")

    def _get_destination(self, destination_id: UUID) -> Destination:
        destination = self._repository.get_destination(destination_id)
        if destination is not None:
            return destination

        raise ControlPlaneNotFoundError("No existe el destino indicado")

    def _get_config(self, config_id: UUID) -> SyncConfig:
        config = self._repository.get_config(config_id)
        if config is not None:
            return config

        raise ControlPlaneNotFoundError("No existe la configuración indicada")


def _build_sync_config(
    config_id: UUID,
    request: SyncConfigRequestDto,
) -> SyncConfig:
    return SyncConfig(
        id=config_id,
        name=request.name,
        source_connection_id=request.source_connection_id,
        destination_id=request.destination_id,
        sync_mode=request.sync_mode,
        tables=tuple(_build_configured_table(table) for table in request.tables),
        enabled=request.enabled,
    )


def _build_configured_table(table: ConfiguredTableDto) -> ConfiguredTable:
    return ConfiguredTable(
        id=uuid4(),
        logical_name=table.logical_name,
        source_schema=table.source_schema,
        source_table=table.source_table,
        cdc_topic=table.cdc_topic,
        destination_table=table.destination_table,
        primary_key_fields=table.primary_key_fields,
        destination_columns=tuple(
            _build_destination_column(column)
            for column in table.destination_columns
        ),
        enabled=table.enabled,
    )


def _build_destination_column(column: DestinationColumnDto) -> DestinationColumn:
    return DestinationColumn(
        name=column.name,
        destination_type=column.destination_type,
        nullable=column.nullable,
    )


def _build_optional_secret_reference(
    *,
    secret_id: UUID,
    name: str,
    credentials: CredentialsDto | None,
) -> SecretReference | None:
    if credentials is None:
        return None

    return _build_secret_reference(
        secret_id=secret_id,
        name=name,
        credentials=credentials,
    )


def _build_secret_reference(
    *,
    secret_id: UUID,
    name: str,
    credentials: CredentialsDto,
) -> SecretReference:
    return SecretReference(
        id=secret_id,
        name=name,
        provider=SecretProvider.INLINE,
        inline_payload={
            "user": credentials.user,
            "password": credentials.password,
        },
    )
