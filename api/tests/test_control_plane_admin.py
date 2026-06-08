from __future__ import annotations

from datetime import datetime
from typing import Mapping
from uuid import UUID

from fastapi.testclient import TestClient

from cdc_sync_api.application.errors import (
    ControlPlaneConflictError,
    KafkaConnectRequestError,
)
from cdc_sync_api.application.services.cdc_connector_compiler_registry import (
    CdcConnectorCompilerRegistry,
)
from cdc_sync_api.application.dto.control_plane_assignment_dto import (
    WorkerConfigAssignmentDto,
)
from cdc_sync_api.application.use_cases.manage_control_plane import (
    ManageControlPlaneUseCase,
)
from cdc_sync_api.application.use_cases.materialize_cdc_connector import (
    MaterializeCdcConnectorUseCase,
)
from cdc_sync_api.domain.control_plane import (
    Destination,
    SecretReference,
    SourceConnection,
    SyncConfig,
    Worker,
    WorkerConfigAssignment,
)
from cdc_sync_api.entrypoints.http.app import build_app
from cdc_sync_api.entrypoints.http.dependencies import (
    get_control_plane_admin_use_case,
    get_materialize_cdc_connector_use_case,
)
from cdc_sync_api.infrastructure.cdc.debezium_postgres_connector_compiler import (
    DebeziumPostgresConnectorCompiler,
)


def test_administrative_flow_creates_config_and_assigns_worker() -> None:
    client = _build_client()

    worker_response = client.post(
        "/api/v1/workers",
        json={
            "worker_id": "local-worker",
            "name": "Worker local",
            "description": "Demo local",
            "enabled": True,
        },
    )
    source_response = client.post(
        "/api/v1/source-connections",
        json=_source_connection_payload(),
    )
    destination_response = client.post(
        "/api/v1/destinations",
        json=_destination_payload(),
    )

    assert worker_response.status_code == 201
    assert source_response.status_code == 201
    assert destination_response.status_code == 201
    assert "credentials_secret_id" not in source_response.json()
    assert "password" not in source_response.text
    assert "password" not in destination_response.text

    config_response = client.post(
        "/api/v1/configs",
        json=_config_payload(
            source_connection_id=source_response.json()["id"],
            destination_id=destination_response.json()["id"],
        ),
    )

    assert config_response.status_code == 201
    assert config_response.json()["tables"][0]["logical_name"] == "customers"

    assignment_response = client.put(
        f"/api/v1/workers/{worker_response.json()['id']}/config-assignment",
        json={"config_id": config_response.json()["id"]},
    )

    assert assignment_response.status_code == 200
    assert assignment_response.json()["worker_id"] == "local-worker"
    assert assignment_response.json()["config_id"] == config_response.json()["id"]


def test_crud_operations_update_and_delete_administrative_entities() -> None:
    client = _build_client()
    worker_id = client.post(
        "/api/v1/workers",
        json={
            "worker_id": "worker-to-update",
            "name": "Worker inicial",
            "enabled": True,
        },
    ).json()["id"]

    update_response = client.put(
        f"/api/v1/workers/{worker_id}",
        json={
            "worker_id": "worker-updated",
            "name": "Worker actualizado",
            "description": None,
            "enabled": False,
        },
    )
    list_response = client.get("/api/v1/workers")
    delete_response = client.delete(f"/api/v1/workers/{worker_id}")
    get_deleted_response = client.get(f"/api/v1/workers/{worker_id}")

    assert update_response.status_code == 200
    assert update_response.json()["worker_id"] == "worker-updated"
    assert list_response.status_code == 200
    assert list_response.json()[0]["enabled"] is False
    assert delete_response.status_code == 204
    assert get_deleted_response.status_code == 404


def test_config_rejects_missing_references() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/configs",
        json=_config_payload(
            source_connection_id="2a3fb8e3-9ea0-4b1d-b6f6-99ab7ab3914e",
            destination_id="8c7f6b66-8952-4c4e-93e4-36fd4e38799b",
        ),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "No existe la conexión de origen indicada"}


def test_validation_errors_are_explicit() -> None:
    client = _build_client()
    source_response = client.post(
        "/api/v1/source-connections",
        json=_source_connection_payload(source_type="mysql"),
    )

    assert source_response.status_code == 422
    assert source_response.json()["detail"] == "source_type debe ser uno de: postgresql"

    source_id = client.post(
        "/api/v1/source-connections",
        json=_source_connection_payload(),
    ).json()["id"]
    destination_id = client.post(
        "/api/v1/destinations",
        json=_destination_payload(),
    ).json()["id"]
    config_response = client.post(
        "/api/v1/configs",
        json=_config_payload(
            source_connection_id=source_id,
            destination_id=destination_id,
            column_name="version",
        ),
    )

    assert config_response.status_code == 422
    assert "columna técnica" in config_response.json()["detail"]


def test_conflicts_are_returned_for_duplicates_and_referenced_deletes() -> None:
    client = _build_client()
    worker_payload = {
        "worker_id": "duplicated-worker",
        "name": "Worker duplicado",
        "enabled": True,
    }

    client.post("/api/v1/workers", json=worker_payload)
    duplicated_response = client.post("/api/v1/workers", json=worker_payload)

    assert duplicated_response.status_code == 409

    source_id = client.post(
        "/api/v1/source-connections",
        json=_source_connection_payload(),
    ).json()["id"]
    destination_id = client.post(
        "/api/v1/destinations",
        json=_destination_payload(),
    ).json()["id"]
    config_id = client.post(
        "/api/v1/configs",
        json=_config_payload(source_connection_id=source_id, destination_id=destination_id),
    ).json()["id"]
    delete_source_response = client.delete(f"/api/v1/source-connections/{source_id}")

    assert delete_source_response.status_code == 409

    worker_id = client.post(
        "/api/v1/workers",
        json={"worker_id": "assigned-worker", "name": "Worker asignado"},
    ).json()["id"]
    client.put(
        f"/api/v1/workers/{worker_id}/config-assignment",
        json={"config_id": config_id},
    )
    delete_config_response = client.delete(f"/api/v1/configs/{config_id}")

    assert delete_config_response.status_code == 409


def test_materializes_cdc_connector_from_source_connection() -> None:
    client, kafka_connect_client = _build_client_with_cdc_materialization()
    source_id = client.post(
        "/api/v1/source-connections",
        json=_source_connection_payload(),
    ).json()["id"]
    destination_id = client.post(
        "/api/v1/destinations",
        json=_destination_payload(),
    ).json()["id"]
    client.post(
        "/api/v1/configs",
        json=_config_payload(source_connection_id=source_id, destination_id=destination_id),
    )

    response = client.put(f"/api/v1/source-connections/{source_id}/cdc-connector")

    assert response.status_code == 200
    assert response.json()["source_connection_id"] == source_id
    assert response.json()["source_type"] == "postgresql"
    assert response.json()["connector_class"] == (
        "io.debezium.connector.postgresql.PostgresConnector"
    )
    assert response.json()["topic_prefix"] == "cdc_sync"
    assert response.json()["captured_tables"] == ["public.customers"]
    assert "password" not in response.text
    assert kafka_connect_client.calls[0][0] == f"cdc-sync-postgresql-{source_id}"
    assert kafka_connect_client.calls[0][1]["database.password"] == "cdc_sync"


def test_cdc_connector_materialization_returns_404_for_missing_source() -> None:
    client, _kafka_connect_client = _build_client_with_cdc_materialization()

    response = client.put(
        "/api/v1/source-connections/2a3fb8e3-9ea0-4b1d-b6f6-99ab7ab3914e/cdc-connector"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "No existe la conexión de origen indicada"}


def test_cdc_connector_materialization_returns_422_for_invalid_config() -> None:
    client, _kafka_connect_client = _build_client_with_cdc_materialization()
    source_id = client.post(
        "/api/v1/source-connections",
        json=_source_connection_payload(),
    ).json()["id"]

    response = client.put(f"/api/v1/source-connections/{source_id}/cdc-connector")

    assert response.status_code == 422
    assert "tablas habilitadas" in response.json()["detail"]


def test_cdc_connector_materialization_returns_502_for_kafka_connect_errors() -> None:
    client, _kafka_connect_client = _build_client_with_cdc_materialization(
        kafka_connect_client=_FailingKafkaConnectClient()
    )
    source_id = client.post(
        "/api/v1/source-connections",
        json=_source_connection_payload(),
    ).json()["id"]
    destination_id = client.post(
        "/api/v1/destinations",
        json=_destination_payload(),
    ).json()["id"]
    client.post(
        "/api/v1/configs",
        json=_config_payload(source_connection_id=source_id, destination_id=destination_id),
    )

    response = client.put(f"/api/v1/source-connections/{source_id}/cdc-connector")

    assert response.status_code == 502
    assert response.json()["detail"] == "Kafka Connect no disponible"


class InMemoryControlPlaneRepository:
    def __init__(self) -> None:
        self.secrets: dict[UUID, SecretReference] = {}
        self.workers: dict[UUID, Worker] = {}
        self.source_connections: dict[UUID, SourceConnection] = {}
        self.destinations: dict[UUID, Destination] = {}
        self.configs: dict[UUID, SyncConfig] = {}
        self.assignments: dict[UUID, WorkerConfigAssignment] = {}

    def list_workers(self) -> tuple[Worker, ...]:
        return tuple(self.workers.values())

    def save_secret_reference(self, secret_reference: SecretReference) -> None:
        self.secrets[secret_reference.id] = secret_reference

    def get_secret_reference(self, secret_id: UUID) -> SecretReference | None:
        return self.secrets.get(secret_id)

    def save_worker(self, worker: Worker) -> None:
        self._ensure_unique_worker_identifier(worker)
        self.workers[worker.id] = worker

    def get_worker(self, worker_id: UUID) -> Worker | None:
        return self.workers.get(worker_id)

    def update_worker(self, worker: Worker) -> bool:
        if worker.id not in self.workers:
            return False

        self._ensure_unique_worker_identifier(worker)
        self.workers[worker.id] = worker
        return True

    def delete_worker(self, worker_id: UUID) -> bool:
        return self.workers.pop(worker_id, None) is not None

    def list_source_connections(self) -> tuple[SourceConnection, ...]:
        return tuple(self.source_connections.values())

    def save_source_connection(self, source_connection: SourceConnection) -> None:
        self.source_connections[source_connection.id] = source_connection

    def save_source_connection_with_credentials(
        self,
        source_connection: SourceConnection,
        credentials: SecretReference,
    ) -> None:
        self.secrets[credentials.id] = credentials
        self.source_connections[source_connection.id] = source_connection

    def get_source_connection(
        self,
        source_connection_id: UUID,
    ) -> SourceConnection | None:
        return self.source_connections.get(source_connection_id)

    def update_source_connection(
        self,
        source_connection: SourceConnection,
        credentials: SecretReference | None,
    ) -> bool:
        if source_connection.id not in self.source_connections:
            return False

        if credentials is not None:
            self.secrets[credentials.id] = credentials

        self.source_connections[source_connection.id] = source_connection
        return True

    def delete_source_connection(self, source_connection_id: UUID) -> bool:
        if source_connection_id not in self.source_connections:
            return False

        if any(
            config.source_connection_id == source_connection_id
            for config in self.configs.values()
        ):
            raise ControlPlaneConflictError(
                "No se puede eliminar una conexión asignada a configs"
            )

        del self.source_connections[source_connection_id]
        return True

    def list_destinations(self) -> tuple[Destination, ...]:
        return tuple(self.destinations.values())

    def save_destination(self, destination: Destination) -> None:
        self.destinations[destination.id] = destination

    def save_destination_with_credentials(
        self,
        destination: Destination,
        credentials: SecretReference,
    ) -> None:
        self.secrets[credentials.id] = credentials
        self.destinations[destination.id] = destination

    def get_destination(self, destination_id: UUID) -> Destination | None:
        return self.destinations.get(destination_id)

    def update_destination(
        self,
        destination: Destination,
        credentials: SecretReference | None,
    ) -> bool:
        if destination.id not in self.destinations:
            return False

        if credentials is not None:
            self.secrets[credentials.id] = credentials

        self.destinations[destination.id] = destination
        return True

    def delete_destination(self, destination_id: UUID) -> bool:
        if destination_id not in self.destinations:
            return False

        if any(config.destination_id == destination_id for config in self.configs.values()):
            raise ControlPlaneConflictError(
                "No se puede eliminar un destino asignado a configs"
            )

        del self.destinations[destination_id]
        return True

    def list_configs(self) -> tuple[SyncConfig, ...]:
        return tuple(self.configs.values())

    def save_config(self, config: SyncConfig) -> None:
        self.configs[config.id] = config

    def get_config(self, config_id: UUID) -> SyncConfig | None:
        return self.configs.get(config_id)

    def update_config(self, config: SyncConfig) -> bool:
        if config.id not in self.configs:
            return False

        self.configs[config.id] = config
        return True

    def delete_config(self, config_id: UUID) -> bool:
        if config_id not in self.configs:
            return False

        if any(
            assignment.config_id == config_id
            for assignment in self.assignments.values()
        ):
            raise ControlPlaneConflictError(
                "No se puede eliminar una configuración asignada"
            )

        del self.configs[config_id]
        return True

    def assign_config_to_worker(self, assignment: WorkerConfigAssignment) -> None:
        self.assignments[assignment.worker_id] = assignment

    def get_worker_by_identifier(self, worker_id: str) -> Worker | None:
        for worker in self.workers.values():
            if worker.worker_id == worker_id:
                return worker

        return None

    def get_assignment_for_worker(
        self,
        worker_id: str,
    ) -> WorkerConfigAssignmentDto | None:
        worker = self.get_worker_by_identifier(worker_id)
        if worker is None:
            return None

        assignment = self.assignments.get(worker.id)
        if assignment is None:
            return None

        return WorkerConfigAssignmentDto(
            worker_internal_id=worker.id,
            worker_id=worker.worker_id,
            config_id=assignment.config_id,
            assigned_at=assignment.assigned_at,
        )

    def _ensure_unique_worker_identifier(self, worker: Worker) -> None:
        for existing_worker in self.workers.values():
            if existing_worker.id == worker.id:
                continue

            if existing_worker.worker_id != worker.worker_id:
                continue

            raise ControlPlaneConflictError(
                "Ya existe un worker con ese identificador"
            )


def _build_client() -> TestClient:
    repository = InMemoryControlPlaneRepository()
    app = build_app()
    app.dependency_overrides[get_control_plane_admin_use_case] = (
        lambda: ManageControlPlaneUseCase(repository)
    )
    return TestClient(app)


def _build_client_with_cdc_materialization(
    kafka_connect_client=None,
) -> tuple[TestClient, "_KafkaConnectClient"]:
    repository = InMemoryControlPlaneRepository()
    app = build_app()
    kafka_client = kafka_connect_client or _KafkaConnectClient()
    app.dependency_overrides[get_control_plane_admin_use_case] = (
        lambda: ManageControlPlaneUseCase(repository)
    )
    app.dependency_overrides[get_materialize_cdc_connector_use_case] = (
        lambda: MaterializeCdcConnectorUseCase(
            repository=repository,
            compiler_registry=CdcConnectorCompilerRegistry(
                (DebeziumPostgresConnectorCompiler(),)
            ),
            kafka_connect_client=kafka_client,
        )
    )
    return TestClient(app), kafka_client


class _KafkaConnectClient:
    def __init__(self) -> None:
        self.calls: tuple[tuple[str, dict[str, str]], ...] = ()

    def put_connector_config(
        self,
        connector_name: str,
        config: Mapping[str, str],
    ) -> None:
        self.calls = self.calls + ((connector_name, dict(config)),)


class _FailingKafkaConnectClient:
    def put_connector_config(
        self,
        connector_name: str,
        config: Mapping[str, str],
    ) -> None:
        raise KafkaConnectRequestError("Kafka Connect no disponible")


def _source_connection_payload(
    *,
    source_type: str = "postgresql",
) -> dict[str, object]:
    return {
        "name": "PostgreSQL local",
        "source_type": source_type,
        "host": "postgres",
        "port": 5432,
        "database_name": "cdc_sync",
        "credentials": {
            "user": "cdc_sync",
            "password": "cdc_sync",
        },
    }


def _destination_payload() -> dict[str, object]:
    return {
        "name": "ClickHouse local",
        "destination_type": "clickhouse",
        "host": "clickhouse",
        "port": 9000,
        "secure": False,
        "database_name": "cdc_sync_analytics",
        "credentials": {
            "user": "cdc_sync",
            "password": "cdc_sync",
        },
    }


def _config_payload(
    *,
    source_connection_id: str,
    destination_id: str,
    column_name: str = "id",
) -> dict[str, object]:
    return {
        "name": "Configuración local",
        "source_connection_id": source_connection_id,
        "destination_id": destination_id,
        "sync_mode": "realtime",
        "enabled": True,
        "tables": [
            {
                "logical_name": "customers",
                "source_schema": "public",
                "source_table": "customers",
                "cdc_topic": "cdc_sync.public.customers",
                "destination_table": "customers",
                "primary_key_fields": ["id"],
                "destination_columns": [
                    {
                        "name": column_name,
                        "destination_type": "UInt64",
                        "nullable": False,
                    },
                    {
                        "name": "email",
                        "destination_type": "String",
                        "nullable": True,
                    },
                ],
                "enabled": True,
            }
        ],
    }
