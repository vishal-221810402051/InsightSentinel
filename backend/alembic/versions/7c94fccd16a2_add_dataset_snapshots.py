"""add dataset snapshots

Revision ID: 7c94fccd16a2
Revises: 9a2d1f5a7b3c
Create Date: 2026-03-10 10:49:26.090466

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql



revision = '7c94fccd16a2'
down_revision = '9a2d1f5a7b3c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dataset_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("column_count", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_dataset_snapshots_dataset_id",
        "dataset_snapshots",
        ["dataset_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_dataset_snapshots_dataset_id", table_name="dataset_snapshots")
    op.drop_table("dataset_snapshots")
