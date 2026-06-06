from uuid import UUID, uuid4

import pytest

from cdc_sync_api.domain.control_plane import (
    ConfiguredTable,
    ControlPlaneValidationError,
    DestinationColumn,
    SecretProvider,
    SecretReference,
    SourceConnection,
    SourceType,
    SyncConfig,
    SyncMode,
)
from cdc_sync_api.infrastructure.cdc.debezium_postgres_connector_compiler import (
    DebeziumPostgresConnectorCompiler,
)


def test_compiles_debezium_postgres_connector_config() -> None:
    source_connection_id = UUID("11111111-1111-1111-1111-111111111111")
    source_connection = _source_connection(source_connection_id)
    config = _sync_config(
        source_connection.id,
        (_configured_table(logical_name="customers", source_table="customers"),),
    )

    compiled_connector = DebeziumPostgresConnectorCompiler().compile(
        _compile_request(source_connection, _secret(), (config,))
    )

    assert compiled_connector.connector_name == (
        "cdc-sync-postgresql-11111111-1111-1111-1111-111111111111"
    )
    assert compiled_connector.connector_class == (
        "io.debezium.connector.postgresql.PostgresConnector"
    )
    assert compiled_connector.topic_prefix == "cdc_sync"
    assert compiled_connector.captured_tables == ("public.customers",)
    assert compiled_connector.config["database.hostname"] == "postgres"
    assert compiled_connector.config["database.port"] == "5432"
    assert compiled_connector.config["database.user"] == "cdc_sync"
    assert compiled_connector.config["database.password"] == "cdc_sync"
    assert compiled_connector.config["table.include.list"] == "public.customers"
    assert compiled_connector.config["slot.name"] == (
        "cdc_sync_11111111111111111111111111111111_slot"
    )
    assert compiled_connector.config["publication.name"] == (
        "cdc_sync_11111111111111111111111111111111_publication"
    )


def test_unions_enabled_tables_from_enabled_configs() -> None:
    source_connection = _source_connection()
    first_config = _sync_config(
        source_connection.id,
        (
            _configured_table(logical_name="orders", source_table="orders"),
            _configured_table(
                logical_name="disabled-products",
                source_table="products",
                enabled=False,
            ),
        ),
    )
    second_config = _sync_config(
        source_connection.id,
        (
            _configured_table(logical_name="customers", source_table="customers"),
            _configured_table(logical_name="orders-copy", source_table="orders"),
        ),
    )
    disabled_config = _sync_config(
        source_connection.id,
        (_configured_table(logical_name="products", source_table="products"),),
        enabled=False,
    )

    compiled_connector = DebeziumPostgresConnectorCompiler().compile(
        _compile_request(
            source_connection,
            _secret(),
            (first_config, second_config, disabled_config),
        )
    )

    assert compiled_connector.captured_tables == (
        "public.customers",
        "public.orders",
    )
    assert compiled_connector.config["table.include.list"] == (
        "public.customers,public.orders"
    )


def test_rejects_inconsistent_topic_prefixes() -> None:
    source_connection = _source_connection()
    config = _sync_config(
        source_connection.id,
        (
            _configured_table(logical_name="customers", source_table="customers"),
            _configured_table(
                logical_name="orders",
                source_table="orders",
                cdc_topic="other_prefix.public.orders",
            ),
        ),
    )

    with pytest.raises(ControlPlaneValidationError, match="topic.prefix"):
        DebeziumPostgresConnectorCompiler().compile(
            _compile_request(source_connection, _secret(), (config,))
        )


def test_rejects_topic_that_does_not_match_table() -> None:
    source_connection = _source_connection()
    config = _sync_config(
        source_connection.id,
        (
            _configured_table(
                logical_name="customers",
                source_table="customers",
                cdc_topic="cdc_sync.public.orders",
            ),
        ),
    )

    with pytest.raises(ControlPlaneValidationError, match="no coincide"):
        DebeziumPostgresConnectorCompiler().compile(
            _compile_request(source_connection, _secret(), (config,))
        )


def test_rejects_connector_without_enabled_tables() -> None:
    source_connection = _source_connection()
    config = _sync_config(
        source_connection.id,
        (
            _configured_table(
                logical_name="disabled-customers",
                source_table="customers",
                enabled=False,
            ),
        ),
    )

    with pytest.raises(ControlPlaneValidationError, match="tablas habilitadas"):
        DebeziumPostgresConnectorCompiler().compile(
            _compile_request(source_connection, _secret(), (config,))
        )


def test_rejects_incomplete_postgres_credentials() -> None:
    source_connection = _source_connection()
    config = _sync_config(
        source_connection.id,
        (_configured_table(logical_name="customers", source_table="customers"),),
    )

    with pytest.raises(ControlPlaneValidationError, match="user y password"):
        DebeziumPostgresConnectorCompiler().compile(
            _compile_request(
                source_connection,
                _secret({"user": "cdc_sync"}),
                (config,),
            )
        )


def test_rejects_ambiguous_postgres_table_identifiers() -> None:
    source_connection = _source_connection()
    config = _sync_config(
        source_connection.id,
        (
            _configured_table(
                logical_name="customers",
                source_schema="public.audit",
                source_table="customers",
            ),
        ),
    )

    with pytest.raises(ControlPlaneValidationError, match="puntos ni comas"):
        DebeziumPostgresConnectorCompiler().compile(
            _compile_request(source_connection, _secret(), (config,))
        )


def _compile_request(
    source_connection: SourceConnection,
    credentials: SecretReference,
    configs: tuple[SyncConfig, ...],
):
    from cdc_sync_api.application.dto.cdc_connector_dto import (
        CdcConnectorCompileRequest,
    )

    return CdcConnectorCompileRequest(
        source_connection=source_connection,
        credentials=credentials,
        configs=configs,
    )


def _source_connection(
    source_connection_id: UUID | None = None,
) -> SourceConnection:
    return SourceConnection(
        id=source_connection_id or uuid4(),
        name="PostgreSQL local",
        source_type=SourceType.POSTGRESQL,
        host="postgres",
        port=5432,
        database_name="cdc_sync",
        credentials_secret_id=uuid4(),
    )


def _secret(payload: dict[str, str] | None = None) -> SecretReference:
    return SecretReference(
        id=uuid4(),
        name=f"source-{uuid4()}",
        provider=SecretProvider.INLINE,
        inline_payload=payload or {"user": "cdc_sync", "password": "cdc_sync"},
    )


def _sync_config(
    source_connection_id: UUID,
    tables: tuple[ConfiguredTable, ...],
    *,
    enabled: bool = True,
) -> SyncConfig:
    return SyncConfig(
        id=uuid4(),
        name=f"Config {uuid4()}",
        source_connection_id=source_connection_id,
        destination_id=uuid4(),
        sync_mode=SyncMode.REALTIME,
        tables=tables,
        enabled=enabled,
    )


def _configured_table(
    *,
    logical_name: str,
    source_table: str,
    source_schema: str = "public",
    cdc_topic: str | None = None,
    enabled: bool = True,
) -> ConfiguredTable:
    topic = cdc_topic or f"cdc_sync.{source_schema}.{source_table}"
    return ConfiguredTable(
        id=uuid4(),
        logical_name=logical_name,
        source_schema=source_schema,
        source_table=source_table,
        cdc_topic=topic,
        destination_table=logical_name,
        primary_key_fields=("id",),
        destination_columns=(
            DestinationColumn(
                name="id",
                destination_type="UInt64",
                nullable=False,
            ),
        ),
        enabled=enabled,
    )
