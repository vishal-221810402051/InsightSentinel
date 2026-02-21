from __future__ import annotations

import uuid
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


from app.db.base import Base


class ColumnStatistics(Base):
    __tablename__ = "column_statistics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    column_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_columns.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    mean = Column(Float, nullable=True)
    std = Column(Float, nullable=True)
    min = Column(Float, nullable=True)
    max = Column(Float, nullable=True)

    outlier_count = Column(Integer, nullable=True)
    outlier_ratio = Column(Float, nullable=True)    

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    column = relationship("DatasetColumn", back_populates="statistics")