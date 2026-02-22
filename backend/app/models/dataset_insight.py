from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class DatasetInsight(Base):
    __tablename__ = "dataset_insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # optional column-level insight
    column_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_columns.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    severity = Column(String(20), nullable=False)  # info | warning | risk
    code = Column(String(64), nullable=False)  # e.g. HIGH_NULL_RATIO
    title = Column(String(200), nullable=False)
    message = Column(String(1000), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    dataset = relationship("Dataset")
    column = relationship("DatasetColumn")
