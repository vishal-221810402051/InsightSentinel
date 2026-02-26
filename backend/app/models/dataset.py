from __future__ import annotations

import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=False, default="")

    row_count = Column(Integer, nullable=False, default=0)
    column_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    columns = relationship(
        "DatasetColumn",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    ingestion_runs = relationship(
        "IngestionRun",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    preview = relationship(
        "DatasetPreview",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
