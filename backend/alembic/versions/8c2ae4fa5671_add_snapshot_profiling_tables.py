"""add snapshot profiling tables

Revision ID: 8c2ae4fa5671
Revises: 7c94fccd16a2
Create Date: 2026-03-10 11:13:25.818664

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql



revision = '8c2ae4fa5671'
down_revision = '7c94fccd16a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "snapshot_columns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("dtype", sa.String(length=100), nullable=False),
        sa.Column("null_count", sa.Integer(), nullable=False),
        sa.Column("distinct_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_snapshot_columns_snapshot_id",
        "snapshot_columns",
        ["snapshot_id"],
    )

    op.create_table(
        "snapshot_statistics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "snapshot_column_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("snapshot_columns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mean", sa.Float(), nullable=True),
        sa.Column("std", sa.Float(), nullable=True),
        sa.Column("min", sa.Float(), nullable=True),
        sa.Column("max", sa.Float(), nullable=True),
        sa.Column("outlier_count", sa.Integer(), nullable=True),
        sa.Column("outlier_ratio", sa.Float(), nullable=True),
        sa.Column("skewness", sa.Float(), nullable=True),
        sa.Column("kurtosis", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_snapshot_statistics_snapshot_column_id",
        "snapshot_statistics",
        ["snapshot_column_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_snapshot_statistics_snapshot_column_id",
        table_name="snapshot_statistics",
    )
    op.drop_table("snapshot_statistics")

    op.drop_index(
        "ix_snapshot_columns_snapshot_id",
        table_name="snapshot_columns",
    )
    op.drop_table("snapshot_columns")
