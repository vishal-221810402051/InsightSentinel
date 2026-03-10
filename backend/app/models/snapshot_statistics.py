from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class SnapshotStatistics(Base):
    __tablename__ = "snapshot_statistics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    snapshot_column_id = Column(
        UUID(as_uuid=True),
        ForeignKey("snapshot_columns.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    mean = Column(Float)
    std = Column(Float)
    min = Column(Float)
    max = Column(Float)
    outlier_count = Column(Integer)
    outlier_ratio = Column(Float)
    skewness = Column(Float)
    kurtosis = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    snapshot_column = relationship("SnapshotColumn")
