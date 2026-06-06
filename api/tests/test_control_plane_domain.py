from datetime import UTC, datetime
from uuid import uuid4

import pytest

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


def test_creates_valid_control_plane_model_for_worker_config() -> None:
    source_secret = SecretReference(
        id=uuid4(),
        name="postgres local",
        provider=SecretProvider.INLINE,
        inline_payload={"user": "cdc_sync", "password": "cdc_sync"},
    )
    destination_secret = SecretReference(
        id=uuid4(),
        name="clickhouse local",
        provider=SecretProvider.INLINE,
        inline_payload={"user": "cdc_sync", "password": "cdc_sync"},
    )
    worker = Worker(id=uuid4(), worker_id="worker-local", name="Worker local")
    source_connection = SourceConnection(
        id=uuid4(),
        name="PostgreSQL local",
        source_type=SourceType.POSTGRESQL,
        host="postgres",
        port=5432,
        database_name="cdc_sync",
        credentials_secret_id=source_secret.id,
    )
    destination = Destination(
        id=uuid4(),
        name="ClickHouse local",
        destination_type=DestinationType.CLICKHOUSE,
        host="clickhouse",
        port=9000,
        secure=False,
        database_name="cdc_sync_analytics",
        credentials_secret_id=destination_secret.id,
    )
    table = _build_configured_table()
    config = SyncConfig(
        id=uuid4(),
        name="Configuración local",
        source_connection_id=source_connection.id,
        destination_id=destination.id,
        sync_mode=SyncMode.REALTIME,
        tables=(table,),
    )
    assignment = WorkerConfigAssignment(
        worker_id=worker.id,
        config_id=config.id,
        assigned_at=datetime(2026, 6, 6, tzinfo=UTC),
    )

    assert config.tables == (table,)
    assert assignment.worker_id == worker.id
    assert assignment.config_id == config.id


def test_rejects_table_without_primary_key() -> None:
    with pytest.raises(ControlPlaneValidationError, match="al menos una PK"):
        _build_configured_table(primary_key_fields=())


def test_rejects_primary_key_missing_from_destination_columns() -> None:
    with pytest.raises(ControlPlaneValidationError, match="debe incluir la PK"):
        _build_configured_table(primary_key_fields=("missing_id",))


def test_rejects_nullable_primary_key_destination_column() -> None:
    with pytest.raises(ControlPlaneValidationError, match="como nullable"):
        _build_configured_table(
            destination_columns=(
                DestinationColumn(
                    name="id",
                    destination_type="UInt64",
                    nullable=True,
                ),
            )
        )


def test_rejects_technical_destination_columns() -> None:
    with pytest.raises(ControlPlaneValidationError, match="columna técnica"):
        DestinationColumn(
            name="version",
            destination_type="UInt64",
            nullable=False,
        )


@pytest.mark.parametrize(
    ("overrides", "expected_message"),
    [
        ({"logical_name": "customers"}, "nombre lógico"),
        ({"cdc_topic": "cdc_sync.public.customers"}, "topic CDC"),
        ({"destination_table": "customers"}, "tabla de destino"),
    ],
)
def test_rejects_duplicated_table_identifiers_inside_config(
    overrides: dict[str, str],
    expected_message: str,
) -> None:
    first_table = _build_configured_table()
    second_table_values = {
        "logical_name": "orders",
        "source_table": "orders",
        "cdc_topic": "cdc_sync.public.orders",
        "destination_table": "orders",
    }
    second_table_values.update(overrides)
    second_table = _build_configured_table(**second_table_values)

    with pytest.raises(ControlPlaneValidationError, match=expected_message):
        SyncConfig(
            id=uuid4(),
            name="Configuración duplicada",
            source_connection_id=uuid4(),
            destination_id=uuid4(),
            sync_mode=SyncMode.REALTIME,
            tables=(first_table, second_table),
        )


def test_rejects_config_without_tables() -> None:
    with pytest.raises(ControlPlaneValidationError, match="al menos una tabla"):
        SyncConfig(
            id=uuid4(),
            name="Configuración vacía",
            source_connection_id=uuid4(),
            destination_id=uuid4(),
            sync_mode=SyncMode.REALTIME,
            tables=(),
        )


def test_rejects_inline_secret_without_payload() -> None:
    with pytest.raises(ControlPlaneValidationError, match="inline_payload"):
        SecretReference(
            id=uuid4(),
            name="Secreto incompleto",
            provider=SecretProvider.INLINE,
            inline_payload=None,
        )


def test_rejects_unsupported_mvp_modes() -> None:
    with pytest.raises(ControlPlaneValidationError, match="source_type"):
        SourceConnection(
            id=uuid4(),
            name="MySQL",
            source_type="mysql",
            host="mysql",
            port=3306,
            database_name="cdc_sync",
            credentials_secret_id=uuid4(),
        )

    with pytest.raises(ControlPlaneValidationError, match="destination_type"):
        Destination(
            id=uuid4(),
            name="BigQuery",
            destination_type="bigquery",
            host="bigquery",
            port=443,
            secure=True,
            database_name="cdc_sync",
            credentials_secret_id=uuid4(),
        )

    with pytest.raises(ControlPlaneValidationError, match="sync_mode"):
        SyncConfig(
            id=uuid4(),
            name="Batch",
            source_connection_id=uuid4(),
            destination_id=uuid4(),
            sync_mode="batch",
            tables=(_build_configured_table(),),
        )


def _build_configured_table(
    *,
    logical_name: str = "customers",
    source_table: str = "customers",
    cdc_topic: str = "cdc_sync.public.customers",
    destination_table: str = "customers",
    primary_key_fields: tuple[str, ...] = ("id",),
    destination_columns: tuple[DestinationColumn, ...] | None = None,
) -> ConfiguredTable:
    if destination_columns is None:
        destination_columns = (
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
        )

    return ConfiguredTable(
        id=uuid4(),
        logical_name=logical_name,
        source_schema="public",
        source_table=source_table,
        cdc_topic=cdc_topic,
        destination_table=destination_table,
        primary_key_fields=primary_key_fields,
        destination_columns=destination_columns,
    )
