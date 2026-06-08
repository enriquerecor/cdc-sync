from __future__ import annotations

from dataclasses import dataclass

from cdc_sync_api.application.dto.cdc_connector_dto import (
    CdcConnectorCompileRequest,
    CompiledCdcConnector,
)
from cdc_sync_api.domain.control_plane import (
    ConfiguredTable,
    ControlPlaneValidationError,
    SecretReference,
    SourceConnection,
    SourceType,
    SyncConfig,
)


POSTGRES_CONNECTOR_CLASS = "io.debezium.connector.postgresql.PostgresConnector"


@dataclass(frozen=True)
class _PostgresCredentials:
    user: str
    password: str


class DebeziumPostgresConnectorCompiler:
    @property
    def source_type(self) -> SourceType:
        return SourceType.POSTGRESQL

    def compile(
        self,
        request: CdcConnectorCompileRequest,
    ) -> CompiledCdcConnector:
        _ensure_postgres_source(request.source_connection)
        credentials = _postgres_credentials(request.credentials)
        enabled_tables = _enabled_tables(request.configs)
        if not enabled_tables:
            raise ControlPlaneValidationError(
                "No hay tablas habilitadas para materializar el conector CDC"
            )

        captured_tables = _captured_tables(enabled_tables)
        topic_prefix = _topic_prefix(enabled_tables)
        connector_name = _connector_name(request.source_connection)

        return CompiledCdcConnector(
            connector_name=connector_name,
            source_connection_id=request.source_connection.id,
            source_type=request.source_connection.source_type,
            connector_class=POSTGRES_CONNECTOR_CLASS,
            topic_prefix=topic_prefix,
            captured_tables=captured_tables,
            config={
                "connector.class": POSTGRES_CONNECTOR_CLASS,
                "database.hostname": request.source_connection.host,
                "database.port": str(request.source_connection.port),
                "database.user": credentials.user,
                "database.password": credentials.password,
                "database.dbname": request.source_connection.database_name,
                "plugin.name": "pgoutput",
                "topic.prefix": topic_prefix,
                "slot.name": _slot_name(request.source_connection),
                "publication.name": _publication_name(request.source_connection),
                "publication.autocreate.mode": "filtered",
                "table.include.list": ",".join(captured_tables),
            },
        )


def _ensure_postgres_source(source_connection: SourceConnection) -> None:
    if source_connection.source_type is SourceType.POSTGRESQL:
        return

    raise ControlPlaneValidationError(
        "DebeziumPostgresConnectorCompiler solo soporta source_type 'postgresql'"
    )


def _postgres_credentials(credentials: SecretReference) -> _PostgresCredentials:
    payload = credentials.inline_payload
    if payload is None:
        raise ControlPlaneValidationError(
            "Las credenciales PostgreSQL deben tener payload inline"
        )

    user = payload.get("user")
    password = payload.get("password")
    if user and password:
        return _PostgresCredentials(user=user, password=password)

    raise ControlPlaneValidationError(
        "Las credenciales PostgreSQL deben incluir user y password"
    )


def _enabled_tables(configs: tuple[SyncConfig, ...]) -> tuple[ConfiguredTable, ...]:
    return tuple(
        table
        for config in configs
        if config.enabled
        for table in config.tables
        if table.enabled
    )


def _captured_tables(tables: tuple[ConfiguredTable, ...]) -> tuple[str, ...]:
    return tuple(sorted({_table_identifier(table) for table in tables}))


def _table_identifier(table: ConfiguredTable) -> str:
    source_schema = _ensure_simple_identifier(table.source_schema, "source_schema")
    source_table = _ensure_simple_identifier(table.source_table, "source_table")
    return f"{source_schema}.{source_table}"


def _ensure_simple_identifier(value: str, label: str) -> str:
    if "." not in value and "," not in value:
        return value

    raise ControlPlaneValidationError(
        f"{label} no puede contener puntos ni comas en el adapter PostgreSQL"
    )


def _topic_prefix(tables: tuple[ConfiguredTable, ...]) -> str:
    prefixes = {_topic_prefix_for_table(table) for table in tables}
    if len(prefixes) == 1:
        return next(iter(prefixes))

    raise ControlPlaneValidationError(
        "Las tablas del mismo origen PostgreSQL deben usar el mismo topic.prefix"
    )


def _topic_prefix_for_table(table: ConfiguredTable) -> str:
    topic_suffix = f".{_table_identifier(table)}"
    if table.cdc_topic.endswith(topic_suffix):
        topic_prefix = table.cdc_topic[: -len(topic_suffix)]
        if topic_prefix:
            return topic_prefix

    raise ControlPlaneValidationError(
        f"El topic CDC '{table.cdc_topic}' no coincide con "
        f"'{table.source_schema}.{table.source_table}'"
    )


def _connector_name(source_connection: SourceConnection) -> str:
    return f"cdc-sync-postgresql-{source_connection.id}"


def _slot_name(source_connection: SourceConnection) -> str:
    return f"cdc_sync_{source_connection.id.hex}_slot"


def _publication_name(source_connection: SourceConnection) -> str:
    return f"cdc_sync_{source_connection.id.hex}_publication"
