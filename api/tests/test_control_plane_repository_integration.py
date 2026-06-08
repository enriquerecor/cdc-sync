from __future__ import annotations

from os import getenv
from urllib.parse import unquote, urlparse
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import Engine

from cdc_sync_api.domain.control_plane import (
    ConfiguredTable,
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
from cdc_sync_api.infrastructure.persistence.control_plane_repository import (
    SqlAlchemyControlPlaneRepository,
)
from cdc_sync_api.infrastructure.persistence.control_plane_tables import (
    CONTROL_PLANE_SCHEMA,
    control_plane_metadata,
    secret_references,
    worker_config_assignments,
)

pytestmark = pytest.mark.skipif(
    getenv("API_REPOSITORY_INTEGRATION_TESTS") != "true",
    reason="Requiere PostgreSQL real y API_REPOSITORY_INTEGRATION_TESTS=true",
)


@pytest.fixture()
def engine() -> Engine:
    test_engine = create_engine(_read_test_database_url())
    _prepare_database(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture()
def repository(engine: Engine) -> SqlAlchemyControlPlaneRepository:
    _truncate_control_plane(engine)
    return SqlAlchemyControlPlaneRepository(engine)


def test_persists_source_and_destination_with_inline_credentials(
    engine: Engine,
    repository: SqlAlchemyControlPlaneRepository,
) -> None:
    source_secret = _secret("source")
    destination_secret = _secret("destination")
    source_connection = _source_connection(source_secret.id)
    destination = _destination(destination_secret.id)

    repository.save_source_connection_with_credentials(
        source_connection,
        source_secret,
    )
    repository.save_destination_with_credentials(destination, destination_secret)

    persisted_source_connection = repository.get_source_connection(source_connection.id)
    persisted_destination = repository.get_destination(destination.id)

    assert persisted_source_connection == source_connection
    assert persisted_destination == destination
    assert not hasattr(persisted_source_connection, "inline_payload")
    assert not hasattr(persisted_destination, "inline_payload")
    assert _secret_payload(engine, source_secret.id) == {
        "user": "cdc_sync",
        "password": "cdc_sync",
    }


def test_rebuilds_complete_config_with_ordered_tables_and_columns(
    repository: SqlAlchemyControlPlaneRepository,
) -> None:
    source_secret = _secret("source")
    destination_secret = _secret("destination")
    source_connection = _source_connection(source_secret.id)
    destination = _destination(destination_secret.id)
    config = _sync_config(source_connection.id, destination.id)

    repository.save_source_connection_with_credentials(
        source_connection,
        source_secret,
    )
    repository.save_destination_with_credentials(destination, destination_secret)
    repository.save_config(config)

    persisted_config = repository.get_config(config.id)

    assert persisted_config == config
    assert persisted_config is not None
    assert persisted_config.tables[0].primary_key_fields == ("id",)
    assert tuple(
        column.name for column in persisted_config.tables[0].destination_columns
    ) == ("id", "email")


def test_upserts_one_effective_config_assignment_per_worker(
    engine: Engine,
    repository: SqlAlchemyControlPlaneRepository,
) -> None:
    source_secret = _secret("source")
    destination_secret = _secret("destination")
    worker = Worker(id=uuid4(), worker_id="worker-local", name="Worker local")
    source_connection = _source_connection(source_secret.id)
    destination = _destination(destination_secret.id)
    first_config = _sync_config(source_connection.id, destination.id, name="Primera")
    second_config = _sync_config(source_connection.id, destination.id, name="Segunda")

    repository.save_worker(worker)
    repository.save_source_connection_with_credentials(
        source_connection,
        source_secret,
    )
    repository.save_destination_with_credentials(destination, destination_secret)
    repository.save_config(first_config)
    repository.save_config(second_config)

    repository.assign_config_to_worker(
        WorkerConfigAssignment(worker_id=worker.id, config_id=first_config.id)
    )
    repository.assign_config_to_worker(
        WorkerConfigAssignment(worker_id=worker.id, config_id=second_config.id)
    )

    assignment = repository.get_assignment_for_worker(worker.worker_id)

    assert assignment is not None
    assert assignment.worker_internal_id == worker.id
    assert assignment.config_id == second_config.id
    assert _assignment_count(engine) == 1


def _prepare_database(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {CONTROL_PLANE_SCHEMA}"))

    control_plane_metadata.create_all(engine)


def _read_test_database_url() -> str:
    database_url = getenv("API_TEST_DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "API_TEST_DATABASE_URL es obligatoria para los tests de integración SQL"
        )

    database_name = unquote(urlparse(database_url).path).lstrip("/")
    if "test" in database_name:
        return database_url

    raise RuntimeError(
        "API_TEST_DATABASE_URL debe apuntar a una base de datos de test"
    )


def _truncate_control_plane(engine: Engine) -> None:
    table_names = ", ".join(
        f"{table.schema}.{table.name}" for table in reversed(control_plane_metadata.sorted_tables)
    )
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))


def _secret(label: str) -> SecretReference:
    return SecretReference(
        id=uuid4(),
        name=f"{label}-{uuid4()}",
        provider=SecretProvider.INLINE,
        inline_payload={"user": "cdc_sync", "password": "cdc_sync"},
    )


def _source_connection(credentials_secret_id: UUID) -> SourceConnection:
    return SourceConnection(
        id=uuid4(),
        name="PostgreSQL local",
        source_type=SourceType.POSTGRESQL,
        host="postgres",
        port=5432,
        database_name="cdc_sync",
        credentials_secret_id=credentials_secret_id,
    )


def _destination(credentials_secret_id: UUID) -> Destination:
    return Destination(
        id=uuid4(),
        name="ClickHouse local",
        destination_type=DestinationType.CLICKHOUSE,
        host="clickhouse",
        port=9000,
        secure=False,
        database_name="cdc_sync_analytics",
        credentials_secret_id=credentials_secret_id,
    )


def _sync_config(
    source_connection_id: UUID,
    destination_id: UUID,
    *,
    name: str = "Configuración local",
) -> SyncConfig:
    return SyncConfig(
        id=uuid4(),
        name=name,
        source_connection_id=source_connection_id,
        destination_id=destination_id,
        sync_mode=SyncMode.REALTIME,
        tables=(
            ConfiguredTable(
                id=uuid4(),
                logical_name=f"customers-{uuid4()}",
                source_schema="public",
                source_table="customers",
                cdc_topic=f"cdc_sync.public.customers.{uuid4()}",
                destination_table=f"customers_{uuid4().hex}",
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
            ),
        ),
    )


def _secret_payload(engine: Engine, secret_id: UUID) -> dict[str, str]:
    with engine.begin() as connection:
        row = connection.execute(
            select(secret_references.c.inline_payload).where(
                secret_references.c.id == secret_id
            )
        ).mappings().one()

    return row["inline_payload"]


def _assignment_count(engine: Engine) -> int:
    with engine.begin() as connection:
        return connection.execute(
            select(func.count()).select_from(worker_config_assignments)
        ).scalar_one()
