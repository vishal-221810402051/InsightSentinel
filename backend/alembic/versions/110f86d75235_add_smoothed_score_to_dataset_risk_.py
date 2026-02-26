"""add smoothed_score to dataset_risk_history

Revision ID: 110f86d75235
Revises: 993a090e24ef
Create Date: 2026-02-24 13:53:44.744944

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



revision = '110f86d75235'
down_revision = '993a090e24ef'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dataset_risk_history",
        sa.Column("smoothed_score", sa.Integer(), nullable=True),
    )
    op.add_column(
        "dataset_risk_history",
        sa.Column("alpha", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dataset_risk_history", "alpha")
    op.drop_column("dataset_risk_history", "smoothed_score")
