"""add owner_id to datasets

Revision ID: 9a2d1f5a7b3c
Revises: 1d1f340161e2
Create Date: 2026-02-27 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "9a2d1f5a7b3c"
down_revision = "1d1f340161e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("datasets", sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True))

    # Preserve existing ownership when user_id already exists.
    op.execute(
        """
        UPDATE datasets
        SET owner_id = user_id
        WHERE owner_id IS NULL
          AND user_id IS NOT NULL;
        """
    )

    # Dev-safe fallback for legacy rows without a user_id.
    op.execute(
        """
        UPDATE datasets
        SET owner_id = (SELECT id FROM users ORDER BY created_at ASC LIMIT 1)
        WHERE owner_id IS NULL;
        """
    )

    op.alter_column("datasets", "owner_id", nullable=False)
    op.create_index("ix_datasets_owner_id", "datasets", ["owner_id"])
    op.create_foreign_key(
        "fk_datasets_owner_id_users",
        "datasets",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("fk_datasets_user_id_users", "datasets", type_="foreignkey")
    op.drop_index("ix_datasets_user_id", table_name="datasets")
    op.drop_column("datasets", "user_id")


def downgrade() -> None:
    op.add_column("datasets", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        """
        UPDATE datasets
        SET user_id = owner_id
        WHERE user_id IS NULL
          AND owner_id IS NOT NULL;
        """
    )
    op.create_index("ix_datasets_user_id", "datasets", ["user_id"])
    op.create_foreign_key(
        "fk_datasets_user_id_users",
        "datasets",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("fk_datasets_owner_id_users", "datasets", type_="foreignkey")
    op.drop_index("ix_datasets_owner_id", table_name="datasets")
    op.drop_column("datasets", "owner_id")
