"""add worker kafka group id

Revision ID: 20260607_000003
Revises: 20260606_000002
Create Date: 2026-06-07 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260607_000003"
down_revision = "20260606_000002"
branch_labels = None
depends_on = None

SCHEMA = "control_plane"


def upgrade() -> None:
    op.add_column(
        "workers",
        sa.Column("kafka_group_id", sa.String(length=160), nullable=True),
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_workers_kafka_group_id",
        "workers",
        "kafka_group_id IS NULL OR length(btrim(kafka_group_id)) > 0",
        schema=SCHEMA,
    )
    op.create_unique_constraint(
        "uq_workers_kafka_group_id",
        "workers",
        ["kafka_group_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_workers_kafka_group_id",
        "workers",
        schema=SCHEMA,
        type_="unique",
    )
    op.drop_constraint(
        "ck_workers_kafka_group_id",
        "workers",
        schema=SCHEMA,
        type_="check",
    )
    op.drop_column("workers", "kafka_group_id", schema=SCHEMA)
