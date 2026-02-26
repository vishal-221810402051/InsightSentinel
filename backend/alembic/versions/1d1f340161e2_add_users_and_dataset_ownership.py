"""add users and dataset ownership

Revision ID: 1d1f340161e2
Revises: 8b63e064f45d
Create Date: 2026-02-26 20:28:37.682980

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql



revision = '1d1f340161e2'
down_revision = '8b63e064f45d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.add_column("datasets", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_datasets_user_id", "datasets", ["user_id"])
    op.create_foreign_key(
        "fk_datasets_user_id_users",
        "datasets",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_datasets_user_id_users", "datasets", type_="foreignkey")
    op.drop_index("ix_datasets_user_id", table_name="datasets")
    op.drop_column("datasets", "user_id")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
