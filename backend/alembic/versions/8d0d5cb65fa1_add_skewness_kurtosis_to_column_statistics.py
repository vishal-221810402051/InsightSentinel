"""add skewness kurtosis to column_statistics

Revision ID: 8d0d5cb65fa1
Revises: 40fd8df4a111
Create Date: 2026-02-22 21:10:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "8d0d5cb65fa1"
down_revision = "40fd8df4a111"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("column_statistics", sa.Column("skewness", sa.Float(), nullable=True))
    op.add_column("column_statistics", sa.Column("kurtosis", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("column_statistics", "kurtosis")
    op.drop_column("column_statistics", "skewness")
