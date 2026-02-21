"""normalize dataset schema constraints

Revision ID: 23995d329c14
Revises: 28e04978099c
Create Date: 2026-02-21

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "23995d329c14"
down_revision = "28e04978099c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- datasets ---
    # Ensure no NULLs before making NOT NULL
    op.execute("UPDATE datasets SET description = '' WHERE description IS NULL;")
    op.execute("UPDATE datasets SET row_count = 0 WHERE row_count IS NULL;")
    op.execute("UPDATE datasets SET column_count = 0 WHERE column_count IS NULL;")

    op.alter_column(
        "datasets",
        "name",
        existing_type=sa.String(length=200),
        type_=sa.String(length=255),
        existing_nullable=False,
        nullable=False,
    )

    op.alter_column(
        "datasets",
        "description",
        existing_type=sa.Text(),
        type_=sa.String(length=1000),
        existing_nullable=True,
        nullable=False,
    )

    op.alter_column(
        "datasets",
        "row_count",
        existing_type=sa.Integer(),
        existing_nullable=True,
        nullable=False,
    )

    op.alter_column(
        "datasets",
        "column_count",
        existing_type=sa.Integer(),
        existing_nullable=True,
        nullable=False,
    )

    # --- dataset_columns ---
    # Add created_at
    op.add_column(
        "dataset_columns",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Ensure no NULLs before making NOT NULL
    op.execute("UPDATE dataset_columns SET null_count = 0 WHERE null_count IS NULL;")
    op.execute("UPDATE dataset_columns SET distinct_count = 0 WHERE distinct_count IS NULL;")

    op.alter_column(
        "dataset_columns",
        "name",
        existing_type=sa.String(length=200),
        type_=sa.String(length=255),
        existing_nullable=False,
        nullable=False,
    )

    op.alter_column(
        "dataset_columns",
        "null_count",
        existing_type=sa.Integer(),
        existing_nullable=True,
        nullable=False,
    )

    op.alter_column(
        "dataset_columns",
        "distinct_count",
        existing_type=sa.Integer(),
        existing_nullable=True,
        nullable=False,
    )

    # --- ingestion_runs ---
    # Ensure no NULLs before making NOT NULL
    op.execute("UPDATE ingestion_runs SET message = 'Ingestion started' WHERE message IS NULL;")

    op.alter_column(
        "ingestion_runs",
        "message",
        existing_type=sa.Text(),
        type_=sa.String(length=500),
        existing_nullable=True,
        nullable=False,
    )


def downgrade() -> None:
    # --- ingestion_runs ---
    op.alter_column(
        "ingestion_runs",
        "message",
        existing_type=sa.String(length=500),
        type_=sa.Text(),
        existing_nullable=False,
        nullable=True,
    )

    # --- dataset_columns ---
    op.alter_column(
        "dataset_columns",
        "distinct_count",
        existing_type=sa.Integer(),
        existing_nullable=False,
        nullable=True,
    )

    op.alter_column(
        "dataset_columns",
        "null_count",
        existing_type=sa.Integer(),
        existing_nullable=False,
        nullable=True,
    )

    op.alter_column(
        "dataset_columns",
        "name",
        existing_type=sa.String(length=255),
        type_=sa.String(length=200),
        existing_nullable=False,
        nullable=False,
    )

    op.drop_column("dataset_columns", "created_at")

    # --- datasets ---
    op.alter_column(
        "datasets",
        "column_count",
        existing_type=sa.Integer(),
        existing_nullable=False,
        nullable=True,
    )

    op.alter_column(
        "datasets",
        "row_count",
        existing_type=sa.Integer(),
        existing_nullable=False,
        nullable=True,
    )

    op.alter_column(
        "datasets",
        "description",
        existing_type=sa.String(length=1000),
        type_=sa.Text(),
        existing_nullable=False,
        nullable=True,
    )

    op.alter_column(
        "datasets",
        "name",
        existing_type=sa.String(length=255),
        type_=sa.String(length=200),
        existing_nullable=False,
        nullable=False,
    )