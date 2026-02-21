from __future__ import annotations

import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    dtype = Column(String(100), nullable=False)
    null_count = Column(Integer, nullable=False, default=0)
    distinct_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    statistics = relationship(
        "ColumnStatistics",
        back_populates="column",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )

    dataset = relationship("Dataset", back_populates="columns")

    