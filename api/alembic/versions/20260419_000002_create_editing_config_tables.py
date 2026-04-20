"""create editing config tables

Revision ID: 20260419_000002
Revises: 20260419_000001
Create Date: 2026-04-19 18:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260419_000002"
down_revision = "20260419_000001"
branch_labels = None
depends_on = None

SCHEMA_NAME = "control_plane"


def upgrade() -> None:
    op.create_table(
        "config_editing",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_config_editing_singleton"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_table(
        "config_editing_source_connection",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("config_id", sa.SmallInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("host", sa.Text(), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("database_name", sa.Text(), nullable=False),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("password", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["config_id"],
            [f"{SCHEMA_NAME}.config_editing.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("config_id", "name"),
        sa.UniqueConstraint("config_id", "position"),
        schema=SCHEMA_NAME,
    )
    op.create_table(
        "config_editing_table",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("config_id", sa.SmallInteger(), nullable=False),
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
            ["config_id"],
            [f"{SCHEMA_NAME}.config_editing.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["config_id", "source_connection_name"],
            [
                f"{SCHEMA_NAME}.config_editing_source_connection.config_id",
                f"{SCHEMA_NAME}.config_editing_source_connection.name",
            ],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("config_id", "logical_name"),
        sa.UniqueConstraint("config_id", "position"),
        schema=SCHEMA_NAME,
    )
    op.create_table(
        "config_editing_table_pk",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("table_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["table_id"],
            [f"{SCHEMA_NAME}.config_editing_table.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("table_id", "position"),
        schema=SCHEMA_NAME,
    )
    op.create_table(
        "config_editing_destination_column",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("table_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("column_type", sa.Text(), nullable=False),
        sa.Column("nullable", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["table_id"],
            [f"{SCHEMA_NAME}.config_editing_table.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("table_id", "position"),
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    op.drop_table("config_editing_destination_column", schema=SCHEMA_NAME)
    op.drop_table("config_editing_table_pk", schema=SCHEMA_NAME)
    op.drop_table("config_editing_table", schema=SCHEMA_NAME)
    op.drop_table("config_editing_source_connection", schema=SCHEMA_NAME)
    op.drop_table("config_editing", schema=SCHEMA_NAME)
