"""add dataset anomaly events

Revision ID: 8b63e064f45d
Revises: 04f3198d6c97
Create Date: 2026-02-26 19:56:18.771296

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql



revision = '8b63e064f45d'
down_revision = '04f3198d6c97'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dataset_anomaly_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("rolling_mean", sa.Float(), nullable=True),
        sa.Column("rolling_std", sa.Float(), nullable=True),
        sa.Column("z_score", sa.Float(), nullable=True),
        sa.Column("window", sa.Integer(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_dataset_anomaly_events_dataset_created",
        "dataset_anomaly_events",
        ["dataset_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_dataset_anomaly_events_dataset_metric_created",
        "dataset_anomaly_events",
        ["dataset_id", "metric", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dataset_anomaly_events_dataset_metric_created",
        table_name="dataset_anomaly_events",
    )
    op.drop_index(
        "ix_dataset_anomaly_events_dataset_created",
        table_name="dataset_anomaly_events",
    )
    op.drop_table("dataset_anomaly_events")
