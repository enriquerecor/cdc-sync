"""create control plane model

Revision ID: 20260606_000002
Revises: 20260419_000001
Create Date: 2026-06-06 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260606_000002"
down_revision = "20260419_000001"
branch_labels = None
depends_on = None

SCHEMA = "control_plane"


def upgrade() -> None:
    op.create_table(
        "secret_references",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("inline_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("external_reference", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_secret_references_name",
        ),
        sa.CheckConstraint(
            "provider = 'inline'",
            name="ck_secret_references_provider",
        ),
        sa.CheckConstraint(
            "inline_payload IS NOT NULL "
            "AND jsonb_typeof(inline_payload) = 'object' "
            "AND inline_payload <> '{}'::jsonb",
            name="ck_secret_references_inline_payload",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_secret_references_name"),
        schema=SCHEMA,
    )

    op.create_table(
        "workers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("length(btrim(worker_id)) > 0", name="ck_workers_worker_id"),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_workers_name"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("worker_id", name="uq_workers_worker_id"),
        schema=SCHEMA,
    )

    op.create_table(
        "source_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("database_name", sa.String(length=160), nullable=False),
        sa.Column("credentials_secret_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_source_connections_name",
        ),
        sa.CheckConstraint(
            "source_type = 'postgresql'",
            name="ck_source_connections_source_type",
        ),
        sa.CheckConstraint(
            "length(btrim(host)) > 0",
            name="ck_source_connections_host",
        ),
        sa.CheckConstraint(
            "port BETWEEN 1 AND 65535",
            name="ck_source_connections_port",
        ),
        sa.CheckConstraint(
            "length(btrim(database_name)) > 0",
            name="ck_source_connections_database_name",
        ),
        sa.ForeignKeyConstraint(
            ["credentials_secret_id"],
            ["control_plane.secret_references.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    op.create_table(
        "destinations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("destination_type", sa.String(length=40), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("secure", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("database_name", sa.String(length=160), nullable=False),
        sa.Column("credentials_secret_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_destinations_name"),
        sa.CheckConstraint(
            "destination_type = 'clickhouse'",
            name="ck_destinations_destination_type",
        ),
        sa.CheckConstraint("length(btrim(host)) > 0", name="ck_destinations_host"),
        sa.CheckConstraint(
            "port BETWEEN 1 AND 65535",
            name="ck_destinations_port",
        ),
        sa.CheckConstraint(
            "length(btrim(database_name)) > 0",
            name="ck_destinations_database_name",
        ),
        sa.ForeignKeyConstraint(
            ["credentials_secret_id"],
            ["control_plane.secret_references.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    op.create_table(
        "configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("source_connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sync_mode", sa.String(length=40), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_configs_name"),
        sa.CheckConstraint("sync_mode = 'realtime'", name="ck_configs_sync_mode"),
        sa.ForeignKeyConstraint(
            ["destination_id"],
            ["control_plane.destinations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_connection_id"],
            ["control_plane.source_connections.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    op.create_table(
        "config_tables",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("logical_name", sa.String(length=160), nullable=False),
        sa.Column("source_schema", sa.String(length=160), nullable=False),
        sa.Column("source_table", sa.String(length=160), nullable=False),
        sa.Column("cdc_topic", sa.String(length=255), nullable=False),
        sa.Column("destination_table", sa.String(length=160), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "length(btrim(logical_name)) > 0",
            name="ck_config_tables_name",
        ),
        sa.CheckConstraint(
            "length(btrim(source_schema)) > 0",
            name="ck_config_tables_source_schema",
        ),
        sa.CheckConstraint(
            "length(btrim(source_table)) > 0",
            name="ck_config_tables_source_table",
        ),
        sa.CheckConstraint(
            "length(btrim(cdc_topic)) > 0",
            name="ck_config_tables_topic",
        ),
        sa.CheckConstraint(
            "length(btrim(destination_table)) > 0",
            name="ck_config_tables_destination_table",
        ),
        sa.CheckConstraint("position >= 0", name="ck_config_tables_position"),
        sa.ForeignKeyConstraint(
            ["config_id"],
            ["control_plane.configs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("config_id", "logical_name", name="uq_config_tables_name"),
        sa.UniqueConstraint("config_id", "cdc_topic", name="uq_config_tables_topic"),
        sa.UniqueConstraint(
            "config_id",
            "destination_table",
            name="uq_config_tables_destination_table",
        ),
        sa.UniqueConstraint("config_id", "position", name="uq_config_tables_position"),
        schema=SCHEMA,
    )

    op.create_table(
        "config_table_primary_keys",
        sa.Column("config_table_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("column_name", sa.String(length=160), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "length(btrim(column_name)) > 0",
            name="ck_config_table_primary_keys_column_name",
        ),
        sa.CheckConstraint(
            "position >= 0",
            name="ck_config_table_primary_keys_position",
        ),
        sa.ForeignKeyConstraint(
            ["config_table_id"],
            ["control_plane.config_tables.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("config_table_id", "column_name"),
        sa.UniqueConstraint(
            "config_table_id",
            "position",
            name="uq_config_table_primary_keys_position",
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "config_table_destination_columns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("config_table_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("destination_type", sa.String(length=160), nullable=False),
        sa.Column("nullable", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_config_table_destination_columns_name",
        ),
        sa.CheckConstraint(
            "name NOT IN ('version', 'deleted')",
            name="ck_config_table_destination_columns_not_technical",
        ),
        sa.CheckConstraint(
            "length(btrim(destination_type)) > 0",
            name="ck_config_table_destination_columns_destination_type",
        ),
        sa.CheckConstraint(
            "position >= 0",
            name="ck_config_table_destination_columns_position",
        ),
        sa.ForeignKeyConstraint(
            ["config_table_id"],
            ["control_plane.config_tables.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "config_table_id",
            "name",
            name="uq_config_table_destination_columns_name",
        ),
        sa.UniqueConstraint(
            "config_table_id",
            "position",
            name="uq_config_table_destination_columns_position",
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "worker_config_assignments",
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["config_id"],
            ["control_plane.configs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["worker_id"],
            ["control_plane.workers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("worker_id"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("worker_config_assignments", schema=SCHEMA)
    op.drop_table("config_table_destination_columns", schema=SCHEMA)
    op.drop_table("config_table_primary_keys", schema=SCHEMA)
    op.drop_table("config_tables", schema=SCHEMA)
    op.drop_table("configs", schema=SCHEMA)
    op.drop_table("destinations", schema=SCHEMA)
    op.drop_table("source_connections", schema=SCHEMA)
    op.drop_table("workers", schema=SCHEMA)
    op.drop_table("secret_references", schema=SCHEMA)
