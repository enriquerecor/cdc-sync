from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

CONTROL_PLANE_SCHEMA = "control_plane"

control_plane_metadata = MetaData(schema=CONTROL_PLANE_SCHEMA)


def _uuid_column(name: str, *, primary_key: bool = False) -> Column:
    return Column(name, UUID(as_uuid=True), primary_key=primary_key)


def _timestamps() -> tuple[Column, Column]:
    return (
        Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
        Column(
            "updated_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )


secret_references = Table(
    "secret_references",
    control_plane_metadata,
    _uuid_column("id", primary_key=True),
    Column("name", String(120), nullable=False),
    Column("provider", String(40), nullable=False),
    Column("inline_payload", JSONB, nullable=False),
    Column("external_reference", String(512), nullable=True),
    *_timestamps(),
    CheckConstraint("length(btrim(name)) > 0", name="ck_secret_references_name"),
    CheckConstraint("provider = 'inline'", name="ck_secret_references_provider"),
    CheckConstraint(
        "inline_payload IS NOT NULL "
        "AND jsonb_typeof(inline_payload) = 'object' "
        "AND inline_payload <> '{}'::jsonb",
        name="ck_secret_references_inline_payload",
    ),
    UniqueConstraint("name", name="uq_secret_references_name"),
)

workers = Table(
    "workers",
    control_plane_metadata,
    _uuid_column("id", primary_key=True),
    Column("worker_id", String(120), nullable=False),
    Column("name", String(160), nullable=False),
    Column("description", Text, nullable=True),
    Column("enabled", Boolean, nullable=False, server_default="true"),
    *_timestamps(),
    CheckConstraint("length(btrim(worker_id)) > 0", name="ck_workers_worker_id"),
    CheckConstraint("length(btrim(name)) > 0", name="ck_workers_name"),
    UniqueConstraint("worker_id", name="uq_workers_worker_id"),
)

source_connections = Table(
    "source_connections",
    control_plane_metadata,
    _uuid_column("id", primary_key=True),
    Column("name", String(160), nullable=False),
    Column("source_type", String(40), nullable=False),
    Column("host", String(255), nullable=False),
    Column("port", Integer, nullable=False),
    Column("database_name", String(160), nullable=False),
    Column(
        "credentials_secret_id",
        UUID(as_uuid=True),
        ForeignKey("control_plane.secret_references.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    *_timestamps(),
    CheckConstraint("length(btrim(name)) > 0", name="ck_source_connections_name"),
    CheckConstraint(
        "source_type = 'postgresql'",
        name="ck_source_connections_source_type",
    ),
    CheckConstraint("length(btrim(host)) > 0", name="ck_source_connections_host"),
    CheckConstraint(
        "port BETWEEN 1 AND 65535",
        name="ck_source_connections_port",
    ),
    CheckConstraint(
        "length(btrim(database_name)) > 0",
        name="ck_source_connections_database_name",
    ),
)

destinations = Table(
    "destinations",
    control_plane_metadata,
    _uuid_column("id", primary_key=True),
    Column("name", String(160), nullable=False),
    Column("destination_type", String(40), nullable=False),
    Column("host", String(255), nullable=False),
    Column("port", Integer, nullable=False),
    Column("secure", Boolean, nullable=False, server_default="false"),
    Column("database_name", String(160), nullable=False),
    Column(
        "credentials_secret_id",
        UUID(as_uuid=True),
        ForeignKey("control_plane.secret_references.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    *_timestamps(),
    CheckConstraint("length(btrim(name)) > 0", name="ck_destinations_name"),
    CheckConstraint(
        "destination_type = 'clickhouse'",
        name="ck_destinations_destination_type",
    ),
    CheckConstraint("length(btrim(host)) > 0", name="ck_destinations_host"),
    CheckConstraint("port BETWEEN 1 AND 65535", name="ck_destinations_port"),
    CheckConstraint(
        "length(btrim(database_name)) > 0",
        name="ck_destinations_database_name",
    ),
)

configs = Table(
    "configs",
    control_plane_metadata,
    _uuid_column("id", primary_key=True),
    Column("name", String(160), nullable=False),
    Column(
        "source_connection_id",
        UUID(as_uuid=True),
        ForeignKey("control_plane.source_connections.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "destination_id",
        UUID(as_uuid=True),
        ForeignKey("control_plane.destinations.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("sync_mode", String(40), nullable=False),
    Column("enabled", Boolean, nullable=False, server_default="true"),
    *_timestamps(),
    CheckConstraint("length(btrim(name)) > 0", name="ck_configs_name"),
    CheckConstraint("sync_mode = 'realtime'", name="ck_configs_sync_mode"),
)

config_tables = Table(
    "config_tables",
    control_plane_metadata,
    _uuid_column("id", primary_key=True),
    Column(
        "config_id",
        UUID(as_uuid=True),
        ForeignKey("control_plane.configs.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("logical_name", String(160), nullable=False),
    Column("source_schema", String(160), nullable=False),
    Column("source_table", String(160), nullable=False),
    Column("cdc_topic", String(255), nullable=False),
    Column("destination_table", String(160), nullable=False),
    Column("enabled", Boolean, nullable=False, server_default="true"),
    Column("position", Integer, nullable=False),
    CheckConstraint("length(btrim(logical_name)) > 0", name="ck_config_tables_name"),
    CheckConstraint(
        "length(btrim(source_schema)) > 0",
        name="ck_config_tables_source_schema",
    ),
    CheckConstraint(
        "length(btrim(source_table)) > 0",
        name="ck_config_tables_source_table",
    ),
    CheckConstraint("length(btrim(cdc_topic)) > 0", name="ck_config_tables_topic"),
    CheckConstraint(
        "length(btrim(destination_table)) > 0",
        name="ck_config_tables_destination_table",
    ),
    CheckConstraint("position >= 0", name="ck_config_tables_position"),
    UniqueConstraint("config_id", "logical_name", name="uq_config_tables_name"),
    UniqueConstraint("config_id", "cdc_topic", name="uq_config_tables_topic"),
    UniqueConstraint(
        "config_id",
        "destination_table",
        name="uq_config_tables_destination_table",
    ),
    UniqueConstraint("config_id", "position", name="uq_config_tables_position"),
)

config_table_primary_keys = Table(
    "config_table_primary_keys",
    control_plane_metadata,
    Column(
        "config_table_id",
        UUID(as_uuid=True),
        ForeignKey("control_plane.config_tables.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("column_name", String(160), primary_key=True),
    Column("position", Integer, nullable=False),
    CheckConstraint(
        "length(btrim(column_name)) > 0",
        name="ck_config_table_primary_keys_column_name",
    ),
    CheckConstraint("position >= 0", name="ck_config_table_primary_keys_position"),
    UniqueConstraint(
        "config_table_id",
        "position",
        name="uq_config_table_primary_keys_position",
    ),
)

config_table_destination_columns = Table(
    "config_table_destination_columns",
    control_plane_metadata,
    _uuid_column("id", primary_key=True),
    Column(
        "config_table_id",
        UUID(as_uuid=True),
        ForeignKey("control_plane.config_tables.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("name", String(160), nullable=False),
    Column("destination_type", String(160), nullable=False),
    Column("nullable", Boolean, nullable=False),
    Column("position", Integer, nullable=False),
    CheckConstraint(
        "length(btrim(name)) > 0",
        name="ck_config_table_destination_columns_name",
    ),
    CheckConstraint(
        "name NOT IN ('version', 'deleted')",
        name="ck_config_table_destination_columns_not_technical",
    ),
    CheckConstraint(
        "length(btrim(destination_type)) > 0",
        name="ck_config_table_destination_columns_destination_type",
    ),
    CheckConstraint(
        "position >= 0",
        name="ck_config_table_destination_columns_position",
    ),
    UniqueConstraint(
        "config_table_id",
        "name",
        name="uq_config_table_destination_columns_name",
    ),
    UniqueConstraint(
        "config_table_id",
        "position",
        name="uq_config_table_destination_columns_position",
    ),
)

worker_config_assignments = Table(
    "worker_config_assignments",
    control_plane_metadata,
    Column(
        "worker_id",
        UUID(as_uuid=True),
        ForeignKey("control_plane.workers.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "config_id",
        UUID(as_uuid=True),
        ForeignKey("control_plane.configs.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "assigned_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)
