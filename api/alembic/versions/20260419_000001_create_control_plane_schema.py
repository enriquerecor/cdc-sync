"""create control plane schema

Revision ID: 20260419_000001
Revises:
Create Date: 2026-04-19 15:45:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260419_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS control_plane"))


def downgrade() -> None:
    op.execute(sa.text("DROP SCHEMA IF EXISTS control_plane CASCADE"))
