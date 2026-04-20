from __future__ import annotations

import sqlalchemy as sa

CONFIG_EDITING_ID = 1
CONTROL_PLANE_SCHEMA = "control_plane"
metadata = sa.MetaData(schema=CONTROL_PLANE_SCHEMA)

config_editing = sa.Table(
    "config_editing",
    metadata,
    sa.Column("id", sa.SmallInteger(), primary_key=True),
    sa.Column("version", sa.BigInteger(), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("id = 1", name="ck_config_editing_singleton"),
)

config_editing_source_connection = sa.Table(
    "config_editing_source_connection",
    metadata,
    sa.Column("id", sa.BigInteger(), primary_key=True),
    sa.Column(
        "config_id",
        sa.SmallInteger(),
        sa.ForeignKey(
            f"{CONTROL_PLANE_SCHEMA}.config_editing.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    ),
    sa.Column("position", sa.Integer(), nullable=False),
    sa.Column("name", sa.Text(), nullable=False),
    sa.Column("host", sa.Text(), nullable=False),
    sa.Column("port", sa.Integer(), nullable=False),
    sa.Column("database_name", sa.Text(), nullable=False),
    sa.Column("username", sa.Text(), nullable=False),
    sa.Column("password", sa.Text(), nullable=False),
    sa.UniqueConstraint("config_id", "name"),
    sa.UniqueConstraint("config_id", "position"),
)

config_editing_table = sa.Table(
    "config_editing_table",
    metadata,
    sa.Column("id", sa.BigInteger(), primary_key=True),
    sa.Column(
        "config_id",
        sa.SmallInteger(),
        sa.ForeignKey(
            f"{CONTROL_PLANE_SCHEMA}.config_editing.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    ),
    sa.Column("position", sa.Integer(), nullable=False),
    sa.Column("logical_name", sa.Text(), nullable=False),
    sa.Column("enabled", sa.Boolean(), nullable=False),
    sa.Column("source_adapter", sa.Text(), nullable=False),
    sa.Column("source_connection_name", sa.Text(), nullable=False),
    sa.Column("source_schema", sa.Text(), nullable=True),
    sa.Column("source_table", sa.Text(), nullable=False),
    sa.Column("source_topic", sa.Text(), nullable=False),
    sa.Column("sync_mode", sa.Text(), nullable=False),
    sa.Column("destination_table", sa.Text(), nullable=False),
    sa.Column("destination_default_nullable", sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(
        ["config_id", "source_connection_name"],
        [
            f"{CONTROL_PLANE_SCHEMA}.config_editing_source_connection.config_id",
            f"{CONTROL_PLANE_SCHEMA}.config_editing_source_connection.name",
        ],
        ondelete="CASCADE",
    ),
    sa.UniqueConstraint("config_id", "logical_name"),
    sa.UniqueConstraint("config_id", "position"),
)

config_editing_table_pk = sa.Table(
    "config_editing_table_pk",
    metadata,
    sa.Column("id", sa.BigInteger(), primary_key=True),
    sa.Column(
        "table_id",
        sa.BigInteger(),
        sa.ForeignKey(
            f"{CONTROL_PLANE_SCHEMA}.config_editing_table.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    ),
    sa.Column("position", sa.Integer(), nullable=False),
    sa.Column("field_name", sa.Text(), nullable=False),
    sa.UniqueConstraint("table_id", "position"),
)

config_editing_destination_column = sa.Table(
    "config_editing_destination_column",
    metadata,
    sa.Column("id", sa.BigInteger(), primary_key=True),
    sa.Column(
        "table_id",
        sa.BigInteger(),
        sa.ForeignKey(
            f"{CONTROL_PLANE_SCHEMA}.config_editing_table.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    ),
    sa.Column("position", sa.Integer(), nullable=False),
    sa.Column("name", sa.Text(), nullable=False),
    sa.Column("column_type", sa.Text(), nullable=False),
    sa.Column("nullable", sa.Boolean(), nullable=True),
    sa.UniqueConstraint("table_id", "position"),
)
