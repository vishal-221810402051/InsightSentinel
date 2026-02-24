"""add dataset risk history

Revision ID: 993a090e24ef
Revises: 81377d5d81c5
Create Date: 2026-02-24 09:27:51.559875

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '993a090e24ef'
down_revision = '81377d5d81c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dataset_risk_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_dataset_risk_history_dataset_id", "dataset_risk_history", ["dataset_id"], unique=False)
    op.create_index(
        "ix_dataset_risk_history_dataset_id_created_at",
        "dataset_risk_history",
        ["dataset_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_dataset_risk_history_dataset_id_created_at", table_name="dataset_risk_history")
    op.drop_index("ix_dataset_risk_history_dataset_id", table_name="dataset_risk_history")
    op.drop_table("dataset_risk_history")
