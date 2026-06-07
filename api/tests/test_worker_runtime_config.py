from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from cdc_sync_api.application.errors import ControlPlaneNotFoundError
from cdc_sync_api.application.use_cases.get_worker_runtime_config import (
    GetWorkerRuntimeConfigUseCase,
)
from cdc_sync_api.domain.control_plane import (
    ConfiguredTable,
    ControlPlaneValidationError,
    Destination,
    DestinationColumn,
    DestinationType,
    SecretProvider,
    SecretReference,
    SourceConnection,
    SourceType,
    SyncConfig,
    SyncMode,
    Worker,
    WorkerConfigAssignment,
)


def test_compiles_runtime_config_with_derived_group_id() -> None:
    worker = _worker(worker_id="local-worker")
    source_connection = _source_connection()
    destination = _destination()
    config = _sync_config(source_connection.id, destination.id)
    repository = _Repository(
        workers={worker.id: worker},
        source_connections={source_connection.id: source_connection},
        destinations={destination.id: destination},
        secrets={destination.credentials_secret_id: _secret(destination.credentials_secret_id)},
        configs={config.id: config},
        assignments={
            worker.id: WorkerConfigAssignment(worker_id=worker.id, config_id=config.id)
        },
    )

    response = _use_case(repository).get_config("local-worker")

    assert response.contract_version == 1
    assert response.worker.worker_id == "local-worker"
    assert response.kafka.bootstrap_servers == "kafka:29092"
    assert response.kafka.client_id == "cdc-sync-worker-local-worker"
    assert response.kafka.group_id == "cdc-sync-worker-local-worker"
    assert response.kafka.topics == ("cdc_sync.public.customers",)
    assert response.destination.adapter == "clickhouse"
    assert response.destination.credentials.user == "cdc_sync"
    assert response.tables["customers"].source.adapter == "debezium_postgres"
    assert response.tables["customers"].enabled is True


def test_compiles_runtime_config_with_explicit_group_id_and_enabled_tables_only() -> None:
    worker = _worker(
        worker_id="local-worker",
        kafka_group_id="custom-consumer-group",
    )
    source_connection = _source_connection()
    destination = _destination()
    config = _sync_config(
        source_connection.id,
        destination.id,
        tables=(
            _configured_table(logical_name="customers", source_table="customers"),
            _configured_table(
                logical_name="orders",
                source_table="orders",
                enabled=False,
            ),
        ),
    )
    repository = _Repository(
        workers={worker.id: worker},
        source_connections={source_connection.id: source_connection},
        destinations={destination.id: destination},
        secrets={destination.credentials_secret_id: _secret(destination.credentials_secret_id)},
        configs={config.id: config},
        assignments={
            worker.id: WorkerConfigAssignment(worker_id=worker.id, config_id=config.id)
        },
    )

    response = _use_case(repository).get_config("local-worker")

    assert response.kafka.group_id == "custom-consumer-group"
    assert response.kafka.topics == ("cdc_sync.public.customers",)
    assert set(response.tables) == {"customers"}


def test_runtime_config_fails_for_missing_worker() -> None:
    with pytest.raises(ControlPlaneNotFoundError, match="worker"):
        _use_case(_Repository()).get_config("missing-worker")


def test_runtime_config_fails_for_worker_without_assignment() -> None:
    worker = _worker()

    with pytest.raises(ControlPlaneNotFoundError, match="configuración efectiva"):
        _use_case(_Repository(workers={worker.id: worker})).get_config(worker.worker_id)


def test_runtime_config_fails_for_disabled_worker() -> None:
    worker = _worker(enabled=False)
    repository = _Repository(workers={worker.id: worker})

    with pytest.raises(ControlPlaneValidationError, match="deshabilitado"):
        _use_case(repository).get_config(worker.worker_id)


def test_runtime_config_fails_for_disabled_config() -> None:
    worker, source_connection, destination, config = _runtime_parts(config_enabled=False)
    repository = _repository_for_runtime(worker, source_connection, destination, config)

    with pytest.raises(ControlPlaneValidationError, match="deshabilitada"):
        _use_case(repository).get_config(worker.worker_id)


def test_runtime_config_fails_for_inconsistent_admin_references() -> None:
    worker, source_connection, destination, config = _runtime_parts()
    repository = _repository_for_runtime(worker, source_connection, destination, config)
    repository.source_connections = {}

    with pytest.raises(ControlPlaneValidationError, match="origen inexistente"):
        _use_case(repository).get_config(worker.worker_id)


def test_runtime_config_fails_without_valid_destination_credentials() -> None:
    worker, source_connection, destination, config = _runtime_parts()
    repository = _repository_for_runtime(worker, source_connection, destination, config)
    repository.secrets = {
        destination.credentials_secret_id: _secret(
            destination.credentials_secret_id,
            payload={"user": "cdc_sync"},
        )
    }

    with pytest.raises(ControlPlaneValidationError, match="user y password"):
        _use_case(repository).get_config(worker.worker_id)


def test_runtime_config_fails_without_enabled_tables() -> None:
    worker, source_connection, destination, config = _runtime_parts(
        tables=(
            _configured_table(
                logical_name="customers",
                source_table="customers",
                enabled=False,
            ),
        )
    )
    repository = _repository_for_runtime(worker, source_connection, destination, config)

    with pytest.raises(ControlPlaneValidationError, match="tabla habilitada"):
        _use_case(repository).get_config(worker.worker_id)


class _Repository:
    def __init__(
        self,
        *,
        workers: dict[UUID, Worker] | None = None,
        source_connections: dict[UUID, SourceConnection] | None = None,
        destinations: dict[UUID, Destination] | None = None,
        secrets: dict[UUID, SecretReference] | None = None,
        configs: dict[UUID, SyncConfig] | None = None,
        assignments: dict[UUID, WorkerConfigAssignment] | None = None,
    ) -> None:
        self.workers = workers or {}
        self.source_connections = source_connections or {}
        self.destinations = destinations or {}
        self.secrets = secrets or {}
        self.configs = configs or {}
        self.assignments = assignments or {}

    def get_worker_by_identifier(self, worker_id: str) -> Worker | None:
        for worker in self.workers.values():
            if worker.worker_id == worker_id:
                return worker

        return None

    def get_assignment_for_worker(self, worker_id: str):
        worker = self.get_worker_by_identifier(worker_id)
        if worker is None:
            return None

        assignment = self.assignments.get(worker.id)
        if assignment is None:
            return None

        from cdc_sync_api.application.dto.control_plane_assignment_dto import (
            WorkerConfigAssignmentDto,
        )

        return WorkerConfigAssignmentDto(
            worker_internal_id=worker.id,
            worker_id=worker.worker_id,
            config_id=assignment.config_id,
            assigned_at=assignment.assigned_at,
        )

    def get_config(self, config_id: UUID) -> SyncConfig | None:
        return self.configs.get(config_id)

    def get_source_connection(
        self,
        source_connection_id: UUID,
    ) -> SourceConnection | None:
        return self.source_connections.get(source_connection_id)

    def get_destination(self, destination_id: UUID) -> Destination | None:
        return self.destinations.get(destination_id)

    def get_secret_reference(self, secret_id: UUID) -> SecretReference | None:
        return self.secrets.get(secret_id)


def _use_case(repository: _Repository) -> GetWorkerRuntimeConfigUseCase:
    return GetWorkerRuntimeConfigUseCase(
        repository=repository,
        kafka_bootstrap_servers="kafka:29092",
        kafka_client_id_prefix="cdc-sync-worker",
        kafka_auto_offset_reset="earliest",
        kafka_poll_timeout_ms=1000,
    )


def _runtime_parts(
    *,
    config_enabled: bool = True,
    tables: tuple[ConfiguredTable, ...] | None = None,
) -> tuple[Worker, SourceConnection, Destination, SyncConfig]:
    worker = _worker()
    source_connection = _source_connection()
    destination = _destination()
    config = _sync_config(
        source_connection.id,
        destination.id,
        enabled=config_enabled,
        tables=tables,
    )
    return worker, source_connection, destination, config


def _repository_for_runtime(
    worker: Worker,
    source_connection: SourceConnection,
    destination: Destination,
    config: SyncConfig,
) -> _Repository:
    return _Repository(
        workers={worker.id: worker},
        source_connections={source_connection.id: source_connection},
        destinations={destination.id: destination},
        secrets={destination.credentials_secret_id: _secret(destination.credentials_secret_id)},
        configs={config.id: config},
        assignments={
            worker.id: WorkerConfigAssignment(worker_id=worker.id, config_id=config.id)
        },
    )


def _worker(
    *,
    worker_id: str = "local-worker",
    kafka_group_id: str | None = None,
    enabled: bool = True,
) -> Worker:
    return Worker(
        id=uuid4(),
        worker_id=worker_id,
        name="Worker local",
        kafka_group_id=kafka_group_id,
        enabled=enabled,
    )


def _source_connection() -> SourceConnection:
    return SourceConnection(
        id=uuid4(),
        name="PostgreSQL local",
        source_type=SourceType.POSTGRESQL,
        host="postgres",
        port=5432,
        database_name="cdc_sync",
        credentials_secret_id=uuid4(),
    )


def _destination() -> Destination:
    return Destination(
        id=uuid4(),
        name="ClickHouse local",
        destination_type=DestinationType.CLICKHOUSE,
        host="clickhouse",
        port=9000,
        secure=False,
        database_name="cdc_sync_analytics",
        credentials_secret_id=uuid4(),
    )


def _secret(
    secret_id: UUID,
    payload: dict[str, str] | None = None,
) -> SecretReference:
    return SecretReference(
        id=secret_id,
        name=f"destination-{secret_id}",
        provider=SecretProvider.INLINE,
        inline_payload=payload or {"user": "cdc_sync", "password": "cdc_sync"},
    )


def _sync_config(
    source_connection_id: UUID,
    destination_id: UUID,
    *,
    enabled: bool = True,
    tables: tuple[ConfiguredTable, ...] | None = None,
) -> SyncConfig:
    return SyncConfig(
        id=uuid4(),
        name="Configuración local",
        source_connection_id=source_connection_id,
        destination_id=destination_id,
        sync_mode=SyncMode.REALTIME,
        enabled=enabled,
        tables=tables
        or (_configured_table(logical_name="customers", source_table="customers"),),
    )


def _configured_table(
    *,
    logical_name: str,
    source_table: str,
    enabled: bool = True,
) -> ConfiguredTable:
    return ConfiguredTable(
        id=uuid4(),
        logical_name=logical_name,
        source_schema="public",
        source_table=source_table,
        cdc_topic=f"cdc_sync.public.{source_table}",
        destination_table=source_table,
        primary_key_fields=("id",),
        destination_columns=(
            DestinationColumn(
                name="id",
                destination_type="UInt64",
                nullable=False,
            ),
            DestinationColumn(
                name="email",
                destination_type="String",
                nullable=True,
            ),
        ),
        enabled=enabled,
    )
