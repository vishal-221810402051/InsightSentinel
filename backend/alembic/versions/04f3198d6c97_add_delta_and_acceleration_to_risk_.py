"""add delta and acceleration to risk history

Revision ID: 04f3198d6c97
Revises: 110f86d75235
Create Date: 2026-02-24 14:19:07.838475

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



revision = '04f3198d6c97'
down_revision = '110f86d75235'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dataset_risk_history",
        sa.Column("delta_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "dataset_risk_history",
        sa.Column("accel_score", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dataset_risk_history", "accel_score")
    op.drop_column("dataset_risk_history", "delta_score")
